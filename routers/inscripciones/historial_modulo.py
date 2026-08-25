from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from dependencies import get_current_user, require_permiso
from models.historial_modulo import HistorialModulo
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.programa_version import ProgramaVersion
from models.programa_version_edicion import ProgramaVersionEdicion
from schemas.historial_modulo import HistorialModuloResponse, HistorialModuloResponseEnriquecido
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/historial-modulo",
    tags=["Historial Modulo"],
    dependencies=[Depends(get_current_user)]
)


def _build_contexto(detalle: DetalleProgramaModulo) -> dict:
    return {
        "programa_nombre": detalle.programa_nombre,
        "programa_version": detalle.programa_version_numero,
        "edicion": detalle.edicion,
        "modulo_sigla": detalle.modulo.sigla,
        "modulo_nombre": detalle.modulo.nombre_modulo,
        "orden": detalle.orden,
        "estado_actual": detalle.estado,
    }


def _enriquecer(h: HistorialModulo, contexto: dict | None) -> HistorialModuloResponseEnriquecido:
    base = HistorialModuloResponse.model_validate(h, from_attributes=True)
    return HistorialModuloResponseEnriquecido(
        **base.model_dump(),
        detalle=contexto,
    )


@router.get("/detalle/{id_detalle}", response_model=list[HistorialModuloResponse])
def listar_por_detalle(id_detalle: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("historial.ver"))):
    return (
        db.query(HistorialModulo)
        .filter(HistorialModulo.id_detalle_programa_modulo == id_detalle)
        .order_by(HistorialModulo.created_at.asc())
        .all()
    )


@router.get("/detalle/{id_detalle}/enriquecido", response_model=list[HistorialModuloResponseEnriquecido])
def listar_por_detalle_enriquecido(id_detalle: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("historial.ver"))):
    historiales = (
        db.query(HistorialModulo)
        .filter(HistorialModulo.id_detalle_programa_modulo == id_detalle)
        .order_by(HistorialModulo.created_at.asc())
        .all()
    )

    detalle_obj = db.query(DetalleProgramaModulo).options(
        joinedload(DetalleProgramaModulo.modulo),
        joinedload(DetalleProgramaModulo.programa_version_edicion)
            .joinedload(ProgramaVersionEdicion.programa_version)
            .joinedload(ProgramaVersion.programa),
    ).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == id_detalle
    ).first()

    contexto = _build_contexto(detalle_obj) if detalle_obj else None
    return [_enriquecer(h, contexto) for h in historiales]


@router.get("/edicion/{id_edicion}", response_model=list[HistorialModuloResponseEnriquecido])
def listar_por_edicion(id_edicion: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("historial.ver"))):
    detalles = db.query(DetalleProgramaModulo).options(
        joinedload(DetalleProgramaModulo.modulo),
        joinedload(DetalleProgramaModulo.programa_version_edicion)
            .joinedload(ProgramaVersionEdicion.programa_version)
            .joinedload(ProgramaVersion.programa),
    ).filter(
        DetalleProgramaModulo.id_programa_version_edicion == id_edicion
    ).all()

    if not detalles:
        return []

    detalle_ids = [d.id_detalle_programa_modulo for d in detalles]
    contexto_map = {d.id_detalle_programa_modulo: _build_contexto(d) for d in detalles}

    historiales = (
        db.query(HistorialModulo)
        .filter(HistorialModulo.id_detalle_programa_modulo.in_(detalle_ids))
        .order_by(HistorialModulo.created_at.asc())
        .all()
    )

    return [
        _enriquecer(h, contexto_map.get(h.id_detalle_programa_modulo))
        for h in historiales
    ]


@router.get("/{id}", response_model=HistorialModuloResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("historial.ver"))):
    historial = db.query(HistorialModulo).filter(
        HistorialModulo.id_historial == id
    ).first()
    if not historial:
        raise HTTPException(status_code=404, detail="No encontrado")
    return historial
