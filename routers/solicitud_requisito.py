from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_permiso
from models.solicitud_requisito import SolicitudRequisito
from models.requisito import Requisito
from schemas.solicitud_requisito import SolicitudRequisitoCreate, SolicitudRequisitoResponse
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/solicitud-requisitos",
    tags=["Requisitos de Incorporación"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=list[SolicitudRequisitoResponse])
def listar_requisitos(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    items = db.query(SolicitudRequisito).filter(
        SolicitudRequisito.estado == "activo"
    ).all()

    requisito_ids = {i.id_requisito for i in items}
    requisitos_map = {
        r.id_requisito: r.nombre
        for r in db.query(Requisito).filter(Requisito.id_requisito.in_(requisito_ids)).all()
    } if requisito_ids else {}

    return [
        SolicitudRequisitoResponse(
            id_solicitud_requisito=i.id_solicitud_requisito,
            id_requisito=i.id_requisito,
            obligatorio=i.obligatorio,
            estado=i.estado,
            requisito_nombre=requisitos_map.get(i.id_requisito),
        )
        for i in items
    ]


@router.post("/", response_model=SolicitudRequisitoResponse, status_code=201)
def agregar_requisito(
    data: SolicitudRequisitoCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    existente = db.query(SolicitudRequisito).filter(
        SolicitudRequisito.id_requisito == data.id_requisito,
        SolicitudRequisito.estado == "activo",
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Este requisito ya está configurado para incorporación")

    requisito = db.query(Requisito).filter(Requisito.id_requisito == data.id_requisito).first()
    if not requisito:
        raise HTTPException(status_code=404, detail="Requisito no encontrado")

    nuevo = SolicitudRequisito(
        id_requisito=data.id_requisito,
        obligatorio=data.obligatorio,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return SolicitudRequisitoResponse(
        id_solicitud_requisito=nuevo.id_solicitud_requisito,
        id_requisito=nuevo.id_requisito,
        obligatorio=nuevo.obligatorio,
        estado=nuevo.estado,
        requisito_nombre=requisito.nombre,
    )


@router.patch("/{id_config}/cambiar-estado")
def cambiar_estado(
    id_config: int,
    body: dict = {},
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    config = db.query(SolicitudRequisito).filter(
        SolicitudRequisito.id_solicitud_requisito == id_config
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")

    nuevo_estado = body.get("estado", "inactivo")
    config.estado = nuevo_estado
    db.commit()
    return {"ok": True}


@router.patch("/{id_config}")
def actualizar_requisito(
    id_config: int,
    body: dict = {},
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    config = db.query(SolicitudRequisito).filter(
        SolicitudRequisito.id_solicitud_requisito == id_config
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")

    if "obligatorio" in body:
        config.obligatorio = body["obligatorio"]
    db.commit()
    return {"ok": True}
