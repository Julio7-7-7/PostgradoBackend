from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.modalidad_academica import ModalidadAcademica
from models.tipo_descuento import TipoDescuento
from models.control_documentacion import ControlDocumentacion
from models.requisito import Requisito
from schemas.detalle_programa_alumno import DetalleProgramaAlumnoCreate, DetalleProgramaAlumnoUpdate, DetalleProgramaAlumnoResponse

router = APIRouter(
    prefix="/detalle-programa-alumno",
    tags=["Detalle Programa Alumno"]
)

def generar_control_documentacion(id_detalle: int, id_modalidad_academica: int, db: Session):
    requisitos = db.query(Requisito).filter(
        Requisito.id_modalidad_academica == id_modalidad_academica,
        Requisito.estado == "activo"
    ).all()
    for requisito in requisitos:
        control = ControlDocumentacion(
            id_detalle_programa_alumno=id_detalle,
            id_requisito=requisito.id_requisito,
            estado="pendiente",
            obligatorio=requisito.obligatorio
        )
        db.add(control)
    db.commit()

@router.post("/", response_model=DetalleProgramaAlumnoResponse, status_code=201)
def crear(data: DetalleProgramaAlumnoCreate, db: Session = Depends(get_db)):
    modalidad = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.id_modalidad_academica == data.id_modalidad_academica
    ).first()
    if not modalidad:
        raise HTTPException(status_code=404, detail="Modalidad académica no encontrada")

    if modalidad.uso_unico:
        usado = db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_alumno == data.id_alumno,
            DetalleProgramaAlumno.id_modalidad_academica == data.id_modalidad_academica,
            DetalleProgramaAlumno.estado.notin_(["postulante"])
        ).first()
        if usado:
            raise HTTPException(
                status_code=400,
                detail=f"El alumno ya utilizó la modalidad '{modalidad.nombre_modalidad}' anteriormente"
            )

    tipo_descuento = None
    if data.id_tipo_descuento:
        tipo_descuento = db.query(TipoDescuento).filter(
            TipoDescuento.id_tipo_descuento == data.id_tipo_descuento
        ).first()
        if not tipo_descuento:
            raise HTTPException(status_code=404, detail="Tipo de descuento no encontrado")
        data.descuento_aplicado = tipo_descuento.porcentaje

    nuevo = DetalleProgramaAlumno(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    generar_control_documentacion(nuevo.id_detalle_programa_alumno, data.id_modalidad_academica, db)

    if tipo_descuento and tipo_descuento.requiere_documento and tipo_descuento.id_requisito_extra:
        control_existente = db.query(ControlDocumentacion).filter(
            ControlDocumentacion.id_detalle_programa_alumno == nuevo.id_detalle_programa_alumno,
            ControlDocumentacion.id_requisito == tipo_descuento.id_requisito_extra
        ).first()
        if control_existente:
            control_existente.obligatorio = True
            db.commit()
        else:
            control_extra = ControlDocumentacion(
                id_detalle_programa_alumno=nuevo.id_detalle_programa_alumno,
                id_requisito=tipo_descuento.id_requisito_extra,
                estado="pendiente",
                obligatorio=True
            )
            db.add(control_extra)
            db.commit()

    db.refresh(nuevo)
    return nuevo

@router.get("/", response_model=list[DetalleProgramaAlumnoResponse])
def listar(db: Session = Depends(get_db)):
    return db.query(DetalleProgramaAlumno).all()

@router.get("/{id}", response_model=DetalleProgramaAlumnoResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="No encontrado")
    return detalle

@router.patch("/{id}", response_model=DetalleProgramaAlumnoResponse)
def editar(id: int, data: DetalleProgramaAlumnoUpdate, db: Session = Depends(get_db)):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="No encontrado")

    if data.id_tipo_descuento:
        tipo_descuento = db.query(TipoDescuento).filter(
            TipoDescuento.id_tipo_descuento == data.id_tipo_descuento
        ).first()
        if not tipo_descuento:
            raise HTTPException(status_code=404, detail="Tipo de descuento no encontrado")
        data.descuento_aplicado = tipo_descuento.porcentaje

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(detalle, key, value)
    db.commit()
    db.refresh(detalle)
    return detalle

@router.delete("/{id}", status_code=204)
def eliminar(id: int, db: Session = Depends(get_db)):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(detalle)
    db.commit()