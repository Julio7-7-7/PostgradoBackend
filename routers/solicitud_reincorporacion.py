from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, joinedload
import json

from database import get_db
from dependencies import get_current_user, require_permiso
from models.solicitud_reincorporacion import SolicitudReincorporacion, SolicitudReincorporacionDocumento
from models.solicitud_requisito import SolicitudRequisito
from models.requisito import Requisito
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.historial_inscripcion import HistorialInscripcion
from schemas.solicitud_reincorporacion import (
    SolicitudReincorporacionCreate,
    SolicitudReincorporacionResponse,
    SolicitudReincorporacionConDetalle,
    SolicitudReincorporacionDocumentoResponse,
)
from schemas.auth import UserResponse
from routers.utils import guardar_documento_base64, inferir_tipo_movimiento

router = APIRouter(
    prefix="/solicitud-reincorporacion",
    tags=["Solicitud de Reincorporación"],
    dependencies=[Depends(get_current_user)],
)


def _cargar_documentos(solicitud: SolicitudReincorporacion, db: Session) -> list[SolicitudReincorporacionDocumentoResponse]:
    req_ids = {d.id_requisito for d in solicitud.documentos}
    requisitos_map = {}
    if req_ids:
        for r in db.query(Requisito).filter(Requisito.id_requisito.in_(req_ids)).all():
            requisitos_map[r.id_requisito] = r.nombre
    return [
        SolicitudReincorporacionDocumentoResponse(
            id_solicitud_reincorporacion_documento=doc.id_solicitud_reincorporacion_documento,
            id_requisito=doc.id_requisito,
            nombre_requisito=requisitos_map.get(doc.id_requisito, ""),
            url_documento=doc.url_documento,
            estado=doc.estado,
            fecha_entrega=doc.fecha_entrega,
        )
        for doc in solicitud.documentos
    ]


@router.post("/solicitar/{id_dpa}", response_model=SolicitudReincorporacionResponse, status_code=201)
def solicitar_reincorporacion(
    id_dpa: int,
    data: SolicitudReincorporacionCreate = Body(default=SolicitudReincorporacionCreate()),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    dpa = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id_dpa,
        DetalleProgramaAlumno.id_alumno == current_user.id_profile,
    ).first()
    if not dpa:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    if dpa.estado != "retirado":
        raise HTTPException(
            status_code=400,
            detail="Solo podés solicitar reincorporación si estás en estado retirado"
        )

    pendiente = db.query(SolicitudReincorporacion).filter(
        SolicitudReincorporacion.id_detalle_programa_alumno == dpa.id_detalle_programa_alumno,
        SolicitudReincorporacion.estado == "pendiente",
    ).first()
    if pendiente:
        raise HTTPException(
            status_code=400,
            detail="Ya tenés una solicitud de reincorporación pendiente para esta inscripción"
        )

    solicitud = SolicitudReincorporacion(
        id_detalle_programa_alumno=dpa.id_detalle_programa_alumno,
        motivo=data.motivo or None,
    )
    db.add(solicitud)
    db.flush()

    requisitos_config = db.query(SolicitudRequisito).filter(
        SolicitudRequisito.estado == "activo",
        SolicitudRequisito.tipo == "reincorporacion",
    ).all()

    for req_config in requisitos_config:
        db.add(SolicitudReincorporacionDocumento(
            id_solicitud_reincorporacion=solicitud.id_solicitud_reincorporacion,
            id_requisito=req_config.id_requisito,
            url_documento="",
            estado="pendiente",
        ))

    db.commit()
    db.refresh(solicitud)

    return SolicitudReincorporacionResponse(
        id_solicitud_reincorporacion=solicitud.id_solicitud_reincorporacion,
        id_detalle_programa_alumno=solicitud.id_detalle_programa_alumno,
        estado=solicitud.estado,
        motivo=solicitud.motivo,
        motivo_rechazo=solicitud.motivo_rechazo,
        created_at=solicitud.created_at,
        updated_at=solicitud.updated_at,
        documentos=_cargar_documentos(solicitud, db),
    )


@router.post("/{id_solicitud}/documentos/{id_doc}/subir")
def subir_documento_reincorporacion(
    id_solicitud: int,
    id_doc: int,
    body: dict = {},
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    solicitud = db.query(SolicitudReincorporacion).filter(
        SolicitudReincorporacion.id_solicitud_reincorporacion == id_solicitud,
        SolicitudReincorporacion.estado == "pendiente",
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada o ya procesada")

    doc = db.query(SolicitudReincorporacionDocumento).filter(
        SolicitudReincorporacionDocumento.id_solicitud_reincorporacion_documento == id_doc,
        SolicitudReincorporacionDocumento.id_solicitud_reincorporacion == id_solicitud,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    url_documento = body.get("url_documento", "")
    if not url_documento:
        raise HTTPException(status_code=400, detail="Se requiere url_documento")

    url = guardar_documento_base64(url_documento, "reincorporacion")
    doc.url_documento = url
    doc.estado = "entregado"
    doc.fecha_entrega = datetime.now()

    db.commit()
    db.refresh(doc)

    return {"ok": True, "url": url}


@router.get("/", response_model=list[SolicitudReincorporacionConDetalle])
def listar_solicitudes_reincorporacion(
    estado: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.ver")),
):
    q = db.query(SolicitudReincorporacion).options(
        joinedload(SolicitudReincorporacion.documentos),
        joinedload(SolicitudReincorporacion.detalle_programa_alumno)
        .joinedload(DetalleProgramaAlumno.alumno),
    )

    if estado:
        q = q.filter(SolicitudReincorporacion.estado == estado)

    q = q.order_by(SolicitudReincorporacion.created_at.desc())

    solicitudes = q.offset((page - 1) * per_page).limit(per_page).all()

    result = []
    for s in solicitudes:
        dpa = s.detalle_programa_alumno
        alumno = dpa.alumno if dpa else None
        pve = dpa.programa_version_edicion if dpa else None
        programa = pve.programa_version.programa if pve and pve.programa_version else None

        result.append(SolicitudReincorporacionConDetalle(
            id_solicitud_reincorporacion=s.id_solicitud_reincorporacion,
            estado=s.estado,
            motivo=s.motivo,
            motivo_rechazo=s.motivo_rechazo,
            created_at=s.created_at,
            id_alumno=dpa.id_alumno if dpa else None,
            alumno_nombre=alumno.nombre if alumno else None,
            alumno_apellido=alumno.apellido if alumno else None,
            alumno_ci=alumno.ci if alumno else None,
            id_detalle_programa_alumno=s.id_detalle_programa_alumno,
            dpa_estado=dpa.estado if dpa else None,
            edicion_numero=pve.edicion if pve else None,
            edicion_anio=pve.anio if pve else None,
            edicion_semestre=pve.semestre if pve else None,
            programa_nombre=programa.nombre_programa if programa else None,
            documentos=_cargar_documentos(s, db),
        ))

    return result


@router.get("/pendientes-count")
def contar_pendientes(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.ver")),
):
    count = db.query(SolicitudReincorporacion).filter(
        SolicitudReincorporacion.estado == "pendiente"
    ).count()
    return {"count": count}


@router.patch("/{id_solicitud}/aprobar", response_model=SolicitudReincorporacionConDetalle)
def aprobar_solicitud_reincorporacion(
    id_solicitud: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    solicitud = db.query(SolicitudReincorporacion).options(
        joinedload(SolicitudReincorporacion.documentos),
        joinedload(SolicitudReincorporacion.detalle_programa_alumno)
        .joinedload(DetalleProgramaAlumno.alumno),
    ).filter(
        SolicitudReincorporacion.id_solicitud_reincorporacion == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"La solicitud ya fue {solicitud.estado}")

    dpa = solicitud.detalle_programa_alumno
    if not dpa:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    if dpa.estado != "retirado":
        raise HTTPException(
            status_code=400,
            detail=f"La inscripción está en estado '{dpa.estado}', se esperaba 'retirado'"
        )

    dpa.estado = "inscrito"

    historial = HistorialInscripcion(
        id_detalle_origen=dpa.id_detalle_programa_alumno,
        id_detalle_destino=dpa.id_detalle_programa_alumno,
        tipo_movimiento=inferir_tipo_movimiento(dpa, dpa, db),
        motivo=solicitud.motivo,
    )
    db.add(historial)

    solicitud.estado = "aprobada"
    solicitud.updated_at = date.today()

    db.commit()
    db.refresh(solicitud)

    alumno = dpa.alumno
    pve = dpa.programa_version_edicion
    programa = pve.programa_version.programa if pve and pve.programa_version else None

    return SolicitudReincorporacionConDetalle(
        id_solicitud_reincorporacion=solicitud.id_solicitud_reincorporacion,
        estado=solicitud.estado,
        motivo=solicitud.motivo,
        motivo_rechazo=solicitud.motivo_rechazo,
        created_at=solicitud.created_at,
        id_alumno=dpa.id_alumno,
        alumno_nombre=alumno.nombre if alumno else None,
        alumno_apellido=alumno.apellido if alumno else None,
        alumno_ci=alumno.ci if alumno else None,
        id_detalle_programa_alumno=solicitud.id_detalle_programa_alumno,
        dpa_estado=dpa.estado,
        edicion_numero=pve.edicion if pve else None,
        edicion_anio=pve.anio if pve else None,
        edicion_semestre=pve.semestre if pve else None,
        programa_nombre=programa.nombre_programa if programa else None,
        documentos=_cargar_documentos(solicitud, db),
    )


@router.patch("/{id_solicitud}/rechazar", response_model=SolicitudReincorporacionConDetalle)
def rechazar_solicitud_reincorporacion(
    id_solicitud: int,
    motivo_rechazo: str = Query(""),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    solicitud = db.query(SolicitudReincorporacion).options(
        joinedload(SolicitudReincorporacion.documentos),
        joinedload(SolicitudReincorporacion.detalle_programa_alumno)
        .joinedload(DetalleProgramaAlumno.alumno),
    ).filter(
        SolicitudReincorporacion.id_solicitud_reincorporacion == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"La solicitud ya fue {solicitud.estado}")

    solicitud.estado = "rechazada"
    solicitud.motivo_rechazo = motivo_rechazo or None
    solicitud.updated_at = date.today()

    db.commit()
    db.refresh(solicitud)

    dpa = solicitud.detalle_programa_alumno
    alumno = dpa.alumno if dpa else None
    pve = dpa.programa_version_edicion if dpa else None
    programa = pve.programa_version.programa if pve and pve.programa_version else None

    return SolicitudReincorporacionConDetalle(
        id_solicitud_reincorporacion=solicitud.id_solicitud_reincorporacion,
        estado=solicitud.estado,
        motivo=solicitud.motivo,
        motivo_rechazo=solicitud.motivo_rechazo,
        created_at=solicitud.created_at,
        id_alumno=dpa.id_alumno if dpa else None,
        alumno_nombre=alumno.nombre if alumno else None,
        alumno_apellido=alumno.apellido if alumno else None,
        alumno_ci=alumno.ci if alumno else None,
        id_detalle_programa_alumno=solicitud.id_detalle_programa_alumno,
        dpa_estado=dpa.estado if dpa else None,
        edicion_numero=pve.edicion if pve else None,
        edicion_anio=pve.anio if pve else None,
        edicion_semestre=pve.semestre if pve else None,
        programa_nombre=programa.nombre_programa if programa else None,
        documentos=_cargar_documentos(solicitud, db),
    )


@router.get("/mis-solicitudes", response_model=list[SolicitudReincorporacionResponse])
def mis_solicitudes_reincorporacion(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    alumno_id = current_user.id_profile

    solicitudes = db.query(SolicitudReincorporacion).options(
        joinedload(SolicitudReincorporacion.documentos),
    ).join(
        DetalleProgramaAlumno
    ).filter(
        DetalleProgramaAlumno.id_alumno == alumno_id,
    ).order_by(SolicitudReincorporacion.created_at.desc()).all()

    return [
        SolicitudReincorporacionResponse(
            id_solicitud_reincorporacion=s.id_solicitud_reincorporacion,
            id_detalle_programa_alumno=s.id_detalle_programa_alumno,
            estado=s.estado,
            motivo=s.motivo,
            motivo_rechazo=s.motivo_rechazo,
            created_at=s.created_at,
            updated_at=s.updated_at,
            documentos=_cargar_documentos(s, db),
        )
        for s in solicitudes
    ]
