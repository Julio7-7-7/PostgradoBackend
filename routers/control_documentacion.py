from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from database import get_db
from models.control_documentacion import ControlDocumentacion
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.requisito import Requisito
from schemas.control_documentacion import ControlDocumentacionCreate, ControlDocumentacionUpdate, ControlDocumentacionResponse

router = APIRouter(
    prefix="/control-documentacion",
    tags=["Control Documentacion"]
)

def verificar_inscripcion_automatica(id_detalle: int, db: Session):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id_detalle
    ).first()

    # buscar controles obligatorios de este alumno específicamente
    controles_obligatorios = db.query(ControlDocumentacion).filter(
        ControlDocumentacion.id_detalle_programa_alumno == id_detalle,
        ControlDocumentacion.obligatorio == True
    ).all()

    if not controles_obligatorios:
        return

    todos_aceptados = all(c.estado == "aceptado" for c in controles_obligatorios)

    if todos_aceptados and detalle.estado == "postulante":
        detalle.estado = "inscrito"
        db.commit()

@router.post("/", response_model=ControlDocumentacionResponse, status_code=201)
def crear(data: ControlDocumentacionCreate, db: Session = Depends(get_db)):
    existente = db.query(ControlDocumentacion).filter(
        ControlDocumentacion.id_detalle_programa_alumno == data.id_detalle_programa_alumno,
        ControlDocumentacion.id_requisito == data.id_requisito
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un control para ese requisito y alumno")
    nuevo = ControlDocumentacion(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.get("/", response_model=list[ControlDocumentacionResponse])
def listar(db: Session = Depends(get_db)):
    return db.query(ControlDocumentacion).all()

@router.get("/{id}", response_model=ControlDocumentacionResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    control = db.query(ControlDocumentacion).filter(
        ControlDocumentacion.id_control_documentacion == id
    ).first()
    if not control:
        raise HTTPException(status_code=404, detail="No encontrado")
    return control

@router.get("/alumno/{id_detalle}", response_model=list[ControlDocumentacionResponse])
def listar_por_alumno(id_detalle: int, db: Session = Depends(get_db)):
    return db.query(ControlDocumentacion).filter(
        ControlDocumentacion.id_detalle_programa_alumno == id_detalle
    ).all()

@router.patch("/{id}", response_model=ControlDocumentacionResponse)
def editar(id: int, data: ControlDocumentacionUpdate, db: Session = Depends(get_db)):
    control = db.query(ControlDocumentacion).filter(
        ControlDocumentacion.id_control_documentacion == id
    ).first()
    if not control:
        raise HTTPException(status_code=404, detail="No encontrado")

    # si se acepta o rechaza agregar fecha de revisión automáticamente
    if data.estado in ["aceptado", "rechazado"]:
        if not data.fecha_revision:
            data.fecha_revision = date.today()
        if data.estado == "rechazado" and not data.observaciones:
            raise HTTPException(status_code=400, detail="Debe proporcionar observaciones al rechazar un documento")

    # si se entrega agregar fecha de entrega automáticamente
    if data.estado == "entregado" and not data.fecha_entrega:
        data.fecha_entrega = date.today()

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(control, key, value)
    db.commit()
    db.refresh(control)

    # verificar si el alumno puede pasar a inscrito
    if data.estado == "aceptado":
        verificar_inscripcion_automatica(control.id_detalle_programa_alumno, db)

    return control

@router.delete("/{id}", status_code=204)
def eliminar(id: int, db: Session = Depends(get_db)):
    control = db.query(ControlDocumentacion).filter(
        ControlDocumentacion.id_control_documentacion == id
    ).first()
    if not control:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(control)
    db.commit()