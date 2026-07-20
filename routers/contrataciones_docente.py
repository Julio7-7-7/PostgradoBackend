from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from database import get_db
from dependencies import get_current_user, require_permiso
from models.contratacion_docente import ContratacionDocente
from models.docente import Docente
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.programa_version_edicion import ProgramaVersionEdicion
from models.programa_version import ProgramaVersion
from schemas.contrataciones_docente import (
    ContratacionDocenteCreate,
    ContratacionDocenteUpdate,
    ContratacionDocenteResponse,
)
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/contratacion-docente",
    tags=["Contratacion Docente"],
    dependencies=[Depends(get_current_user)]
)


def verificar_disponibilidad(db, id_docente, id_detalle_modulo):
    detalle = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == id_detalle_modulo
    ).first()
    if not detalle:
        return

    edicion_id = detalle.id_programa_version_edicion
    nuevo_ini = detalle.fecha_inicio
    nuevo_fin = detalle.fecha_fin

    activas = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_docente == id_docente,
        ContratacionDocente.estado != "truncado",
    ).all()

    otros_detalle_ids = [c.id_detalle_modulo for c in activas if c.id_detalle_modulo != id_detalle_modulo]
    otros_detalles_map = {}
    if otros_detalle_ids:
        otros_detalles = db.query(DetalleProgramaModulo).filter(
            DetalleProgramaModulo.id_detalle_programa_modulo.in_(otros_detalle_ids)
        ).all()
        otros_detalles_map = {d.id_detalle_programa_modulo: d for d in otros_detalles}

    if nuevo_ini and nuevo_fin:
        for c in activas:
            if c.id_detalle_modulo == id_detalle_modulo:
                continue
            otro_detalle = otros_detalles_map.get(c.id_detalle_modulo)
            if not otro_detalle:
                continue
            if otro_detalle.fecha_inicio and otro_detalle.fecha_fin:
                if otro_detalle.fecha_inicio < nuevo_fin and otro_detalle.fecha_fin > nuevo_ini:
                    raise HTTPException(
                        status_code=400,
                        detail="El docente ya tiene una contratación activa en el rango de fechas indicado",
                    )

    # Regla 2: máximo 2 por edición del programa
    count_misma_edicion = db.query(ContratacionDocente).join(
        DetalleProgramaModulo,
        ContratacionDocente.id_detalle_modulo == DetalleProgramaModulo.id_detalle_programa_modulo,
    ).filter(
        ContratacionDocente.id_docente == id_docente,
        ContratacionDocente.estado != "truncado",
        ContratacionDocente.id_detalle_modulo != id_detalle_modulo,
        DetalleProgramaModulo.id_programa_version_edicion == edicion_id,
    ).count()
    if count_misma_edicion >= 2:
        raise HTTPException(
            status_code=400,
            detail="El docente ya tiene el máximo de 2 contrataciones en esta edición del programa",
        )


def query_base(db):
    return db.query(ContratacionDocente).options(
        joinedload(ContratacionDocente.docente),
        joinedload(ContratacionDocente.detalle_modulo),
    )


@router.post("/", response_model=ContratacionDocenteResponse, status_code=201)
def crear(data: ContratacionDocenteCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.crear"))):
    if not db.query(Docente).filter(Docente.id_docente == data.id_docente).first():
        raise HTTPException(status_code=400, detail="El docente especificado no existe")
    if not db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == data.id_detalle_modulo
    ).first():
        raise HTTPException(status_code=400, detail="El detalle de módulo especificado no existe")

    activa = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_detalle_modulo == data.id_detalle_modulo,
        ContratacionDocente.estado != "truncado",
    ).first()
    if activa:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una contratación activa para este módulo. Trúncala antes de crear una nueva.",
        )

    verificar_disponibilidad(db, data.id_docente, data.id_detalle_modulo)

    nuevo = ContratacionDocente(**data.model_dump())
    detalle = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == data.id_detalle_modulo
    ).first()
    if detalle:
        nuevo.fecha_inicio = detalle.fecha_inicio
        nuevo.fecha_fin = detalle.fecha_fin
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return query_base(db).filter(
        ContratacionDocente.id_contratacion == nuevo.id_contratacion
    ).first()


@router.get("/", response_model=list[ContratacionDocenteResponse])
def listar(
    docente_id: int | None = None,
    detalle_id: int | None = None,
    estado: str | None = None,
    q: str | None = None,
    programa_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("contrataciones.ver")),
):
    query = query_base(db)
    if docente_id:
        query = query.filter(ContratacionDocente.id_docente == docente_id)
    if detalle_id:
        query = query.filter(ContratacionDocente.id_detalle_modulo == detalle_id)
    if estado:
        query = query.filter(ContratacionDocente.estado == estado)
    if q:
        query = query.join(ContratacionDocente.docente).filter(
            or_(
                Docente.nombre.ilike(f"%{q}%"),
                Docente.apellido.ilike(f"%{q}%"),
            )
        )
    if programa_id:
        query = (
            query
            .join(ContratacionDocente.detalle_modulo)
            .join(DetalleProgramaModulo.programa_version_edicion)
            .join(ProgramaVersionEdicion.programa_version)
            .filter(ProgramaVersion.id_programa == programa_id)
        )
    return query.all()


@router.get("/{id}", response_model=ContratacionDocenteResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.ver"))):
    contratacion = query_base(db).filter(
        ContratacionDocente.id_contratacion == id
    ).first()
    if not contratacion:
        raise HTTPException(status_code=404, detail="Contratación no encontrada")
    return contratacion


@router.patch("/{id}", response_model=ContratacionDocenteResponse)
def editar(id: int, data: ContratacionDocenteUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.editar"))):
    contratacion = query_base(db).filter(
        ContratacionDocente.id_contratacion == id
    ).first()
    if not contratacion:
        raise HTTPException(status_code=404, detail="Contratación no encontrada")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(contratacion, key, value)

    db.commit()
    db.refresh(contratacion)
    return query_base(db).filter(
        ContratacionDocente.id_contratacion == id
    ).first()


@router.patch("/{id}/truncar", response_model=ContratacionDocenteResponse)
def truncar(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.editar"))):
    contratacion = query_base(db).filter(
        ContratacionDocente.id_contratacion == id
    ).first()
    if not contratacion:
        raise HTTPException(status_code=404, detail="Contratación no encontrada")
    if contratacion.estado == "truncado":
        raise HTTPException(status_code=400, detail="La contratación ya está truncada")
    if contratacion.estado == "formalizado":
        raise HTTPException(
            status_code=400,
            detail="No se puede truncar una contratación formalizada",
        )
    contratacion.estado = "truncado"
    db.commit()
    db.refresh(contratacion)
    return query_base(db).filter(
        ContratacionDocente.id_contratacion == id
    ).first()
