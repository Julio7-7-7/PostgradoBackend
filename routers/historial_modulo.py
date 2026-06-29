from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models.historial_modulo import HistorialModulo
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.programa_version import ProgramaVersion
from models.programa_version_edicion import ProgramaVersionEdicion
from schemas.historial_modulo import HistorialModuloResponse, HistorialModuloResponseEnriquecido

router = APIRouter(
    prefix="/historial-modulo",
    tags=["Historial Modulo"]
)

@router.get("/detalle/{id_detalle}", response_model=list[HistorialModuloResponse])
def listar_por_detalle(id_detalle: int, db: Session = Depends(get_db)):
    return (
        db.query(HistorialModulo)
        .filter(HistorialModulo.id_detalle_programa_modulo == id_detalle)
        .order_by(HistorialModulo.created_at.desc())
        .all()
    )

@router.get("/detalle/{id_detalle}/enriquecido", response_model=list[HistorialModuloResponseEnriquecido])
def listar_por_detalle_enriquecido(id_detalle: int, db: Session = Depends(get_db)):
    historiales = (
        db.query(HistorialModulo)
        .filter(HistorialModulo.id_detalle_programa_modulo == id_detalle)
        .order_by(HistorialModulo.created_at.desc())
        .all()
    )

    detalle = db.query(DetalleProgramaModulo).options(
        joinedload(DetalleProgramaModulo.modulo),
        joinedload(DetalleProgramaModulo.programa_version_edicion)
            .joinedload(ProgramaVersionEdicion.programa_version)
            .joinedload(ProgramaVersion.programa),
    ).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == id_detalle
    ).first()

    contexto = None
    if detalle:
        contexto = {
            "programa_nombre": detalle.programa_nombre,
            "programa_version": detalle.programa_version_numero,
            "edicion": detalle.edicion,
            "modulo_sigla": detalle.modulo.sigla,
            "modulo_nombre": detalle.modulo.nombre_modulo,
            "orden": detalle.orden,
        }

    return [
        HistorialModuloResponseEnriquecido.model_validate({
            **{c.name: getattr(h, c.name) for c in h.__table__.columns},
            "detalle": contexto,
        })
        for h in historiales
    ]

@router.get("/{id}", response_model=HistorialModuloResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    historial = db.query(HistorialModulo).filter(
        HistorialModulo.id_historial == id
    ).first()
    if not historial:
        raise HTTPException(status_code=404, detail="No encontrado")
    return historial
