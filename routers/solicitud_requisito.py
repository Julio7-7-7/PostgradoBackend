from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_permiso
from models.solicitud_requisito import SolicitudRequisito
from models.requisito import Requisito
from models.tipo_solicitud import TipoSolicitud
from schemas.solicitud_requisito import SolicitudRequisitoCreate, SolicitudRequisitoResponse
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/solicitud-requisitos",
    tags=["Requisitos de Incorporación"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=list[SolicitudRequisitoResponse])
def listar_requisitos(
    id_tipo_solicitud: int = Query(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    items = db.query(SolicitudRequisito).filter(
        SolicitudRequisito.estado == "activo",
        SolicitudRequisito.id_tipo_solicitud == id_tipo_solicitud,
    ).all()

    requisito_ids = {i.id_requisito for i in items}
    requisitos_map = {
        r.id_requisito: r.nombre
        for r in db.query(Requisito).filter(Requisito.id_requisito.in_(requisito_ids)).all()
    } if requisito_ids else {}

    tipo_ids = {i.id_tipo_solicitud for i in items}
    tipo_map = {
        t.id_tipo_solicitud: t.codigo
        for t in db.query(TipoSolicitud).filter(TipoSolicitud.id_tipo_solicitud.in_(tipo_ids)).all()
    } if tipo_ids else {}

    return [
        SolicitudRequisitoResponse(
            id_solicitud_requisito=i.id_solicitud_requisito,
            id_requisito=i.id_requisito,
            id_tipo_solicitud=i.id_tipo_solicitud,
            estado=i.estado,
            tipo_codigo=tipo_map.get(i.id_tipo_solicitud),
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
    tipo = db.query(TipoSolicitud).filter(TipoSolicitud.id_tipo_solicitud == data.id_tipo_solicitud).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de solicitud no encontrado")

    existente = db.query(SolicitudRequisito).filter(
        SolicitudRequisito.id_requisito == data.id_requisito,
        SolicitudRequisito.estado == "activo",
        SolicitudRequisito.id_tipo_solicitud == data.id_tipo_solicitud,
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Este requisito ya está configurado para este tipo de solicitud")

    requisito = db.query(Requisito).filter(Requisito.id_requisito == data.id_requisito).first()
    if not requisito:
        raise HTTPException(status_code=404, detail="Requisito no encontrado")

    nuevo = SolicitudRequisito(
        id_requisito=data.id_requisito,
        id_tipo_solicitud=data.id_tipo_solicitud,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return SolicitudRequisitoResponse(
        id_solicitud_requisito=nuevo.id_solicitud_requisito,
        id_requisito=nuevo.id_requisito,
        id_tipo_solicitud=nuevo.id_tipo_solicitud,
        estado=nuevo.estado,
        tipo_codigo=tipo.codigo,
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
