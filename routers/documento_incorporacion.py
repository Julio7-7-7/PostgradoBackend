from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_permiso
from models.documento_incorporacion import DocumentoIncorporacion
from models.detalle_programa_alumno import DetalleProgramaAlumno
from schemas.documento_incorporacion import (
    DocumentoIncorporacionCreate,
    DocumentoIncorporacionUpdate,
    DocumentoIncorporacionResponse,
)
from schemas.auth import UserResponse
from routers.utils import guardar_documento_base64, eliminar_foto

router = APIRouter(
    prefix="/documento-incorporacion",
    tags=["Documento de Incorporación"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=DocumentoIncorporacionResponse, status_code=201)
def crear_documento(
    data: DocumentoIncorporacionCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.crear")),
):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == data.id_detalle_programa_alumno
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    nuevo = DocumentoIncorporacion(**data.model_dump())
    db.add(nuevo)
    db.flush()
    db.refresh(nuevo)
    return nuevo


@router.get("/por-inscripcion/{id_detalle}", response_model=list[DocumentoIncorporacionResponse])
def documentos_por_inscripcion(
    id_detalle: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.ver")),
):
    return db.query(DocumentoIncorporacion).filter(
        DocumentoIncorporacion.id_detalle_programa_alumno == id_detalle
    ).order_by(DocumentoIncorporacion.id_documento_incorporacion).all()


@router.patch("/{id_documento}", response_model=DocumentoIncorporacionResponse)
def actualizar_documento(
    id_documento: int,
    data: DocumentoIncorporacionUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.crear")),
):
    doc = db.query(DocumentoIncorporacion).filter(
        DocumentoIncorporacion.id_documento_incorporacion == id_documento
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    update_data = data.model_dump(exclude_unset=True)

    if "url_documento" in update_data and update_data["url_documento"]:
        old_url = doc.url_documento
        try:
            url = guardar_documento_base64(update_data["url_documento"], "incorporacion")
            update_data["url_documento"] = url
        except Exception:
            pass
        if old_url and update_data.get("url_documento") != old_url:
            eliminar_foto(old_url)

    if update_data.get("estado") == "aceptado" and not doc.fecha_revision:
        update_data["fecha_revision"] = date.today()
    elif update_data.get("estado") == "rechazado" and not doc.fecha_revision:
        update_data["fecha_revision"] = date.today()

    for key, value in update_data.items():
        setattr(doc, key, value)

    db.flush()
    db.refresh(doc)
    return doc
