from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from datetime import date
from pydantic import BaseModel
import math
from database import get_db
from dependencies import get_current_user, require_permiso
from models.control_documentacion import ControlDocumentacion
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.alumno import Alumno
from models.usuario import Usuario
from models.usuario_rol import UsuarioRol
from models.requisito import Requisito
from schemas.control_documentacion import ControlDocumentacionCreate, ControlDocumentacionUpdate, ControlDocumentacionResponse, PaginatedControlDocumentacionResponse
from schemas.auth import UserResponse
from routers.utils import guardar_documento_base64, eliminar_foto

router = APIRouter(
    prefix="/control-documentacion",
    tags=["Control Documentacion"],
    dependencies=[Depends(get_current_user)]
)


class SubirDocumentoRequest(BaseModel):
    url_documento: str


def _es_alumno_actual(usuario: UserResponse, id_alumno: int, db: Session) -> bool:
    """Check if the current user IS the student (even via different roles)."""
    if usuario.profile_type == "alumno" and usuario.id_profile == id_alumno:
        return True
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id_alumno).first()
    if not alumno or not alumno.id_usuario:
        return False
    return alumno.id_usuario == usuario.id_usuario


def verificar_inscripcion_automatica(id_detalle: int, db: Session):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id_detalle
    ).first()

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


def _verificar_ownership_detalle(id_detalle: int, current_user: UserResponse, db: Session):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id_detalle,
        DetalleProgramaAlumno.id_alumno == current_user.id_profile,
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    return detalle


@router.get("/mis-documentos/{id_detalle}", response_model=list[ControlDocumentacionResponse])
def mis_documentos(id_detalle: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    _verificar_ownership_detalle(id_detalle, current_user, db)
    return db.query(ControlDocumentacion).options(
        joinedload(ControlDocumentacion.requisito)
    ).filter(
        ControlDocumentacion.id_detalle_programa_alumno == id_detalle
    ).all()


@router.post("/{id}/subir-documento", response_model=ControlDocumentacionResponse)
def subir_documento(id: int, data: SubirDocumentoRequest, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    control = db.query(ControlDocumentacion).filter(
        ControlDocumentacion.id_control_documentacion == id
    ).first()
    if not control:
        raise HTTPException(status_code=404, detail="No encontrado")

    _verificar_ownership_detalle(control.id_detalle_programa_alumno, current_user, db)

    if control.estado == "aceptado":
        raise HTTPException(status_code=400, detail="El documento ya fue aceptado")

    if control.url_documento:
        eliminar_foto(control.url_documento)

    url = guardar_documento_base64(data.url_documento, "documentos")
    control.url_documento = url
    control.estado = "entregado"
    control.fecha_entrega = date.today()
    control.observaciones = None
    db.commit()
    db.refresh(control)
    return control


@router.post("/", response_model=ControlDocumentacionResponse, status_code=201)
def crear(data: ControlDocumentacionCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("documentos.revisar"))):
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


@router.get("/", response_model=PaginatedControlDocumentacionResponse)
def listar(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("documentos.revisar")),
):
    query = db.query(ControlDocumentacion).options(
        joinedload(ControlDocumentacion.requisito)
    )

    if search:
        like = f"%{search}%"
        query = query.join(
            DetalleProgramaAlumno,
            ControlDocumentacion.id_detalle_programa_alumno == DetalleProgramaAlumno.id_detalle_programa_alumno
        ).join(
            Alumno,
            DetalleProgramaAlumno.id_alumno == Alumno.id_alumno
        ).filter(
            Alumno.nombre.ilike(like) | Alumno.apellido.ilike(like) | Alumno.ci.ilike(like)
        )

    total = query.count()
    pages = math.ceil(total / per_page) if total else 0
    offset = (page - 1) * per_page
    items = query.order_by(ControlDocumentacion.id_control_documentacion).offset(offset).limit(per_page).all()

    return PaginatedControlDocumentacionResponse(
        items=items, total=total, page=page, per_page=per_page, pages=pages
    )


@router.get("/{id}", response_model=ControlDocumentacionResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("documentos.revisar"))):
    control = db.query(ControlDocumentacion).filter(
        ControlDocumentacion.id_control_documentacion == id
    ).first()
    if not control:
        raise HTTPException(status_code=404, detail="No encontrado")
    return control


@router.get("/alumno/{id_detalle}", response_model=list[ControlDocumentacionResponse])
def listar_por_alumno(id_detalle: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("documentos.revisar"))):
    return db.query(ControlDocumentacion).filter(
        ControlDocumentacion.id_detalle_programa_alumno == id_detalle
    ).all()


@router.patch("/{id}", response_model=ControlDocumentacionResponse)
def editar(id: int, data: ControlDocumentacionUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("documentos.aprobar"))):
    control = db.query(ControlDocumentacion).filter(
        ControlDocumentacion.id_control_documentacion == id
    ).first()
    if not control:
        raise HTTPException(status_code=404, detail="No encontrado")

    if data.estado in ["aceptado", "rechazado"]:
        detalle = db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == control.id_detalle_programa_alumno
        ).first()
        if detalle and _es_alumno_actual(current_user, detalle.id_alumno, db):
            raise HTTPException(status_code=403, detail="No podés aprobar o rechazar tu propia documentación")
        if not data.fecha_revision:
            data.fecha_revision = date.today()
        if data.estado == "rechazado" and not data.observaciones:
            raise HTTPException(status_code=400, detail="Debe proporcionar observaciones al rechazar un documento")

    if data.estado == "entregado" and not data.fecha_entrega:
        data.fecha_entrega = date.today()

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(control, key, value)
    db.commit()
    db.refresh(control)

    if data.estado == "aceptado":
        verificar_inscripcion_automatica(control.id_detalle_programa_alumno, db)

    return control


@router.delete("/{id}", status_code=204)
def eliminar(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("documentos.revisar"))):
    control = db.query(ControlDocumentacion).filter(
        ControlDocumentacion.id_control_documentacion == id
    ).first()
    if not control:
        raise HTTPException(status_code=404, detail="No encontrado")
    if control.url_documento:
        eliminar_foto(control.url_documento)
    db.delete(control)
    db.commit()
