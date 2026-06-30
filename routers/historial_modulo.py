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

    detalle_obj = db.query(DetalleProgramaModulo).options(
        joinedload(DetalleProgramaModulo.modulo),
        joinedload(DetalleProgramaModulo.programa_version_edicion)
            .joinedload(ProgramaVersionEdicion.programa_version)
            .joinedload(ProgramaVersion.programa),
    ).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == id_detalle
    ).first()

    contexto = None
    if detalle_obj:
        contexto = {
            "programa_nombre": detalle_obj.programa_nombre,
            "programa_version": detalle_obj.programa_version_numero,
            "edicion": detalle_obj.edicion,
            "modulo_sigla": detalle_obj.modulo.sigla,
            "modulo_nombre": detalle_obj.modulo.nombre_modulo,
            "orden": detalle_obj.orden,
        }

    return [
        HistorialModuloResponseEnriquecido(
            **HistorialModuloResponse.model_validate(h, from_attributes=True).model_dump(),
            detalle=contexto,
        )
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
