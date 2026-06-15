from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.historial_modulo import HistorialModulo
from schemas.detalle_programa_modulo import DetalleProgramaModuloCreate, DetalleProgramaModuloUpdate, DetalleProgramaModuloResponse

router = APIRouter(
    prefix="/detalle-programa-modulo",
    tags=["Detalle Programa Modulo"]
)

ESTADOS_CON_MOTIVO = {"pausado", "reprogramado"}
MOTIVO_AUTO_EN_CURSO = "Cambiado a estado en curso por fechas"
MOTIVO_AUTO_FINALIZADO = "Cambiado a estado finalizado por fecha de fin"

ESTADO_TRANSICIONES = {
    "programado": {"en_curso"},
    "en_curso": {"pausado", "finalizado"},
    "pausado": {"reprogramado", "en_curso"},
    "reprogramado": {"programado", "en_curso"},
    "finalizado": set(),
}

def validar_transicion(estado_actual: str, estado_nuevo: str):
    permitidos = ESTADO_TRANSICIONES.get(estado_actual, set())
    if estado_nuevo not in permitidos:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se puede cambiar de '{estado_actual}' a '{estado_nuevo}'. "
                f"Transiciones permitidas: {', '.join(sorted(permitidos)) if permitidos else 'ninguna'}"
            )
        )

def query_base(db):
    return db.query(DetalleProgramaModulo).options(
        joinedload(DetalleProgramaModulo.modulo),
        joinedload(DetalleProgramaModulo.docente),
        joinedload(DetalleProgramaModulo.modalidad),
    )

def actualizar_estado_auto(detalle: DetalleProgramaModulo, db: Session) -> bool:
    hoy = date.today()

    if detalle.estado == "programado" and detalle.fecha_inicio and detalle.fecha_inicio <= hoy:
        detalle.estado = "en_curso"
        historial = HistorialModulo(
            id_detalle_programa_modulo=detalle.id_detalle_programa_modulo,
            estado_anterior="programado",
            estado_nuevo="en_curso",
            motivo=MOTIVO_AUTO_EN_CURSO,
            fecha_inicio_original=detalle.fecha_inicio,
            fecha_fin_original=detalle.fecha_fin,
        )
        db.add(historial)
        db.commit()
        return True

    if detalle.estado == "en_curso" and detalle.fecha_fin and detalle.fecha_fin < hoy:
        detalle.estado = "finalizado"
        historial = HistorialModulo(
            id_detalle_programa_modulo=detalle.id_detalle_programa_modulo,
            estado_anterior="en_curso",
            estado_nuevo="finalizado",
            motivo=MOTIVO_AUTO_FINALIZADO,
            fecha_inicio_original=detalle.fecha_inicio,
            fecha_fin_original=detalle.fecha_fin,
        )
        db.add(historial)
        db.commit()
        return True

    return False

@router.post("/", response_model=DetalleProgramaModuloResponse, status_code=201)
def crear(data: DetalleProgramaModuloCreate, db: Session = Depends(get_db)):
    orden_existente = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == data.id_programa_version_edicion,
        DetalleProgramaModulo.orden == data.orden
    ).first()
    if orden_existente:
        raise HTTPException(status_code=400, detail=f"Ya existe un módulo con orden {data.orden} en esta edición")
    nuevo = DetalleProgramaModulo(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.get("/", response_model=list[DetalleProgramaModuloResponse])
def listar(edicion_id: int | None = None, db: Session = Depends(get_db)):
    query = query_base(db)
    if edicion_id:
        query = query.filter(DetalleProgramaModulo.id_programa_version_edicion == edicion_id)
    resultados = query.all()
    cambios = False
    for d in resultados:
        if actualizar_estado_auto(d, db):
            cambios = True
    if cambios:
        resultados = query.all()
    return resultados

@router.get("/{id}", response_model=DetalleProgramaModuloResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    detalle = query_base(db).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == id
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="No encontrado")
    if actualizar_estado_auto(detalle, db):
        detalle = query_base(db).filter(
            DetalleProgramaModulo.id_detalle_programa_modulo == id
        ).first()
    return detalle

@router.patch("/{id}", response_model=DetalleProgramaModuloResponse)
def editar(id: int, data: DetalleProgramaModuloUpdate, db: Session = Depends(get_db)):
    detalle = query_base(db).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == id
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="No encontrado")

    actualizar_estado_auto(detalle, db)

    # validar transición de estado
    if data.estado:
        validar_transicion(detalle.estado, data.estado)

        if data.estado in ESTADOS_CON_MOTIVO:
            if not data.motivo:
                raise HTTPException(
                    status_code=400,
                    detail=f"El campo motivo es obligatorio cuando el estado es {data.estado}"
                )
            if len(data.motivo.strip()) < 5:
                raise HTTPException(
                    status_code=400,
                    detail="El motivo debe tener al menos 5 caracteres"
                )

        historial = HistorialModulo(
            id_detalle_programa_modulo=id,
            estado_anterior=detalle.estado,
            estado_nuevo=data.estado,
            motivo=data.motivo if data.estado in ESTADOS_CON_MOTIVO else f"Cambio manual de '{detalle.estado}' a '{data.estado}'",
            fecha_inicio_original=detalle.fecha_inicio,
            fecha_fin_original=detalle.fecha_fin
        )
        db.add(historial)

    # validar orden si se cambia
    if data.orden is not None:
        orden_existente = db.query(DetalleProgramaModulo).filter(
            DetalleProgramaModulo.id_programa_version_edicion == detalle.id_programa_version_edicion,
            DetalleProgramaModulo.orden == data.orden,
            DetalleProgramaModulo.id_detalle_programa_modulo != id
        ).first()
        if orden_existente:
            raise HTTPException(status_code=400, detail=f"Ya existe un módulo con orden {data.orden} en esta edición")

    for key, value in data.model_dump(exclude_unset=True, exclude={"motivo"}).items():
        setattr(detalle, key, value)

    db.commit()
    detalle = query_base(db).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == id
    ).first()
    return detalle
