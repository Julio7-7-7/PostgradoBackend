from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import date, datetime
from database import get_db
from models.programa_version_edicion import ProgramaVersionEdicion
from models.programa_version import ProgramaVersion
from models.programa import Programa
from models.tipo_programa import TipoPrograma
from models.modulo import Modulo
from models.detalle_programa_modulo import DetalleProgramaModulo
from schemas.programa_version_edicion import ProgramaVersionEdicionCreate, ProgramaVersionEdicionUpdate, ProgramaVersionEdicionResponse

router = APIRouter(
    prefix="/programa-version-edicion",
    tags=["Programa Version Edicion"]
)

def calcular_semestre_anio(db: Session, id_programa_version: int) -> tuple[int, int]:
    ultima = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version == id_programa_version
    ).order_by(ProgramaVersionEdicion.edicion.desc()).first()

    if ultima:
        if ultima.semestre == 1:
            return (2, ultima.anio)
        else:
            return (1, ultima.anio + 1)

    ahora = datetime.now()
    semestre = 1 if ahora.month <= 6 else 2
    return (semestre, ahora.year)

def validar_cupo(id_programa_version: int, cupo_maximo: int | None, db: Session):
    if cupo_maximo is None:
        return
    pv = db.query(ProgramaVersion).filter(
        ProgramaVersion.id_programa_version == id_programa_version
    ).first()
    if not pv:
        raise HTTPException(status_code=404, detail="Versión de programa no encontrada")
    programa = db.query(Programa).filter(Programa.id_programa == pv.id_programa).first()
    tipo = db.query(TipoPrograma).filter(TipoPrograma.id_tipo_programa == programa.id_tipo_programa).first()
    if tipo.cupo_minimo and cupo_maximo:
        if cupo_maximo < tipo.cupo_minimo:
            raise HTTPException(
                status_code=400,
                detail=f"El cupo máximo ({cupo_maximo}) no puede ser menor al cupo mínimo del tipo de programa ({tipo.cupo_minimo})"
            )

def obtener_tipo_programa(db: Session, id_programa_version: int) -> TipoPrograma:
    pv = db.query(ProgramaVersion).filter(
        ProgramaVersion.id_programa_version == id_programa_version
    ).first()
    if not pv:
        raise HTTPException(status_code=404, detail="Versión no encontrada")
    programa = db.query(Programa).filter(Programa.id_programa == pv.id_programa).first()
    if not programa:
        raise HTTPException(status_code=404, detail="Programa no encontrado")
    tipo = db.query(TipoPrograma).filter(TipoPrograma.id_tipo_programa == programa.id_tipo_programa).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de programa no encontrado")
    return tipo

def validar_fechas(fecha_inicio: date | None, fecha_fin: date | None, tipo: TipoPrograma, *, es_historico: bool = False):
    hoy = date.today()

    if es_historico:
        pass
    elif fecha_inicio and fecha_inicio < hoy:
        raise HTTPException(
            status_code=400,
            detail="La fecha de inicio no puede ser anterior al día de hoy"
        )

    if fecha_inicio and fecha_fin:
        if fecha_fin <= fecha_inicio:
            raise HTTPException(
                status_code=400,
                detail="La fecha de fin debe ser posterior a la fecha de inicio"
            )

        if tipo.duracion_minima_meses:
            diff_meses = (fecha_fin.year - fecha_inicio.year) * 12 + (fecha_fin.month - fecha_inicio.month)
            if fecha_fin.day < fecha_inicio.day:
                diff_meses -= 1

            if diff_meses < tipo.duracion_minima_meses:
                raise HTTPException(
                    status_code=400,
                    detail=f"La duración mínima para este tipo de programa ({tipo.nombre}) es de {tipo.duracion_minima_meses} mes(es)"
                )

def validar_fecha_inicio_unica(db: Session, id_programa_version: int, fecha_inicio: date | None, excluir_id: int | None = None, *, es_historico: bool = False):
    if not fecha_inicio:
        return
    if es_historico:
        return
    query = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version == id_programa_version,
        ProgramaVersionEdicion.fecha_inicio == fecha_inicio
    )
    if excluir_id:
        query = query.filter(ProgramaVersionEdicion.id_programa_version_edicion != excluir_id)
    if query.first():
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una edición con fecha de inicio {fecha_inicio} para esta versión"
        )

def validar_gestion_fecha(semestre: int | None, anio: int | None, fecha_inicio: date | None, *, es_historico: bool = False):
    if not semestre or not anio or not fecha_inicio or es_historico:
        return
    if semestre == 1 and fecha_inicio.month > 6:
        raise HTTPException(
            status_code=400,
            detail=f"El semestre 1 no coincide con la fecha {fecha_inicio} que está en el segundo semestre"
        )
    if semestre == 2 and fecha_inicio.month <= 6:
        raise HTTPException(
            status_code=400,
            detail=f"El semestre 2 no coincide con la fecha {fecha_inicio} que está en el primer semestre"
        )

def query_base(db):
    return db.query(ProgramaVersionEdicion).options(
        joinedload(ProgramaVersionEdicion.programa_version)
        .joinedload(ProgramaVersion.programa)
        .joinedload(Programa.tipo_programa)
    )

def actualizar_estado_edicion(id_edicion: int, db: Session) -> bool:
    edicion = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id_edicion
    ).first()
    if not edicion:
        return False

    detalles = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == id_edicion
    ).all()
    if not detalles:
        return False

    estados = [d.estado for d in detalles]

    if all(e == "finalizado" for e in estados):
        nuevo = "finalizado"
    elif any(e == "reprogramado" for e in estados) and not any(e == "finalizado" for e in estados):
        nuevo = "reprogramado"
    elif any(e in ("en_curso", "reprogramado") for e in estados):
        nuevo = "en_curso"
    elif any(e == "finalizado" for e in estados):
        nuevo = "en_curso"
    else:
        nuevo = "programado"

    if edicion.estado != nuevo:
        edicion.estado = nuevo
        return True
    return False

@router.post("/", response_model=ProgramaVersionEdicionResponse, status_code=201)
def crear(data: ProgramaVersionEdicionCreate, db: Session = Depends(get_db)):
    validar_cupo(data.id_programa_version, data.cupo_maximo, db)
    tipo = obtener_tipo_programa(db, data.id_programa_version)
    validar_fechas(data.fecha_inicio, data.fecha_fin, tipo, es_historico=data.es_historico)
    validar_fecha_inicio_unica(db, data.id_programa_version, data.fecha_inicio, es_historico=data.es_historico)

    semestre = data.semestre if data.semestre else None
    anio = data.anio if data.anio else None
    if not semestre or not anio:
        semestre, anio = calcular_semestre_anio(db, data.id_programa_version)
    validar_gestion_fecha(semestre, anio, data.fecha_inicio, es_historico=data.es_historico)

    data_dict = data.model_dump(exclude={"semestre", "anio", "edicion", "estado"})
    if data.edicion:
        num_edicion = data.edicion
        existe = db.query(ProgramaVersionEdicion).filter(
            ProgramaVersionEdicion.id_programa_version == data.id_programa_version,
            ProgramaVersionEdicion.edicion == data.edicion
        ).first()
        if existe:
            raise HTTPException(status_code=400, detail=f"Ya existe la edición #{data.edicion} para esta versión")
    else:
        num_edicion = db.query(ProgramaVersionEdicion).filter(
            ProgramaVersionEdicion.id_programa_version == data.id_programa_version
        ).count() + 1
    nueva = ProgramaVersionEdicion(
        **data_dict,
        edicion=num_edicion,
        semestre=semestre,
        anio=anio,
        estado="programado"
    )
    db.add(nueva)
    db.flush()

    modulos = db.query(Modulo).filter(
        Modulo.id_programa_version == data.id_programa_version,
        Modulo.estado == "activo"
    ).order_by(Modulo.sigla).all()

    if not modulos:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se puede crear la edición porque la versión no tiene módulos activos. Cree al menos un módulo activo primero."
        )

    for orden, modulo in enumerate(modulos, start=1):
        detalle = DetalleProgramaModulo(
            id_programa_version_edicion=nueva.id_programa_version_edicion,
            id_modulo=modulo.id_modulo,
            orden=orden,
            estado="programado"
        )
        db.add(detalle)

    db.commit()
    db.refresh(nueva)
    return nueva

@router.get("/", response_model=list[ProgramaVersionEdicionResponse])
def listar(programa_version_id: int | None = None, activas: bool | None = None, db: Session = Depends(get_db)):
    query = query_base(db)
    if programa_version_id:
        query = query.filter(ProgramaVersionEdicion.id_programa_version == programa_version_id)
    if activas:
        query = query.filter(ProgramaVersionEdicion.estado.in_(["programado", "en_curso", "reprogramado"]))
    query = query.order_by(ProgramaVersionEdicion.fecha_inicio.asc().nullslast())
    return query.all()

@router.get("/{id}", response_model=ProgramaVersionEdicionResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    pve = query_base(db).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id
    ).first()
    if not pve:
        raise HTTPException(status_code=404, detail="No encontrado")
    return pve

@router.patch("/{id}", response_model=ProgramaVersionEdicionResponse)
def editar(id: int, data: ProgramaVersionEdicionUpdate, db: Session = Depends(get_db)):
    pve = query_base(db).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id
    ).first()
    if not pve:
        raise HTTPException(status_code=404, detail="No encontrado")

    if data.cupo_maximo is not None:
        validar_cupo(pve.id_programa_version, data.cupo_maximo, db)

    update_data = data.model_dump(exclude_unset=True)
    tiene_fechas = "fecha_inicio" in update_data or "fecha_fin" in update_data
    historico = update_data.get("es_historico", pve.es_historico)

    if tiene_fechas:
        tipo = obtener_tipo_programa(db, pve.id_programa_version)
        fecha_inicio = update_data.get("fecha_inicio", pve.fecha_inicio)
        fecha_fin = update_data.get("fecha_fin", pve.fecha_fin)
        validar_fechas(fecha_inicio, fecha_fin, tipo, es_historico=historico)
        if "fecha_inicio" in update_data:
            validar_fecha_inicio_unica(db, pve.id_programa_version, fecha_inicio, excluir_id=id, es_historico=historico)

    if "semestre" in update_data or "anio" in update_data or "fecha_inicio" in update_data:
        semestre = update_data.get("semestre", pve.semestre)
        anio = update_data.get("anio", pve.anio)
        fecha_inicio = update_data.get("fecha_inicio", pve.fecha_inicio)
        validar_gestion_fecha(semestre, anio, fecha_inicio, es_historico=historico)

    for key, value in update_data.items():
        setattr(pve, key, value)

    db.commit()
    pve = query_base(db).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id
    ).first()
    return pve
