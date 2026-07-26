from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sql_func
import math
from database import get_db
from dependencies import get_current_user, require_permiso
from models.solicitud_incorporacion import SolicitudIncorporacion
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.programa_version_edicion import ProgramaVersionEdicion
from models.programa_version import ProgramaVersion
from models.programa import Programa
from models.alumno import Alumno
from models.requisito import Requisito
from models.historial_inscripcion import HistorialInscripcion
from schemas.solicitud_incorporacion import (
    SolicitudIncorporacionCreate,
    AprobarSolicitudRequest,
    SolicitudIncorporacionResponse,
    SolicitudIncorporacionConDetalle,
)
from schemas.auth import UserResponse
from routers.utils import guardar_documento_base64, eliminar_foto

router = APIRouter(
    prefix="/solicitud-incorporacion",
    tags=["Solicitud de Incorporación"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/solicitar", response_model=SolicitudIncorporacionResponse, status_code=201)
def solicitar_incorporacion(
    data: SolicitudIncorporacionCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    alumno_id = current_user.id_profile
    es_migracion = not data.id_programa_version_edicion

    carta_url = guardar_documento_base64(data.url_documento, "incorporacion")

    requisito = None
    if data.id_requisito:
        requisito = db.query(Requisito).filter(Requisito.id_requisito == data.id_requisito).first()

    if es_migracion:
        return _solicitar_migracion(alumno_id, carta_url, requisito, data, db)
    else:
        return _solicitar_primera_incorporacion(alumno_id, carta_url, requisito, data, db)


def _solicitar_primera_incorporacion(alumno_id, carta_url, requisito, data, db):
    pve = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == data.id_programa_version_edicion
    ).first()
    if not pve:
        raise HTTPException(status_code=404, detail="Edición no encontrada")

    if pve.estado != "en_curso":
        raise HTTPException(
            status_code=400,
            detail="La solicitud de incorporación solo está disponible para ediciones en curso"
        )

    pv = pve.programa_version
    inscripcion_activa = db.query(DetalleProgramaAlumno).join(
        ProgramaVersionEdicion,
        DetalleProgramaAlumno.id_programa_version_edicion == ProgramaVersionEdicion.id_programa_version_edicion
    ).filter(
        DetalleProgramaAlumno.id_alumno == alumno_id,
        ProgramaVersionEdicion.id_programa_version == pv.id_programa_version,
        DetalleProgramaAlumno.estado.in_({"postulante", "observado", "inscrito"}),
        ProgramaVersionEdicion.id_programa_version_edicion != data.id_programa_version_edicion,
    ).first()
    if inscripcion_activa:
        raise HTTPException(
            status_code=400,
            detail="Ya tenés una inscripción activa en otra edición de este programa"
        )

    existente_dpa = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_alumno == alumno_id,
        DetalleProgramaAlumno.id_programa_version_edicion == data.id_programa_version_edicion,
    ).first()

    if existente_dpa:
        solicitud_previa = db.query(SolicitudIncorporacion).filter(
            SolicitudIncorporacion.id_detalle_programa_alumno == existente_dpa.id_detalle_programa_alumno,
        ).first()

        if solicitud_previa and solicitud_previa.estado == "pendiente":
            raise HTTPException(
                status_code=400,
                detail="Ya tenés una solicitud de incorporación pendiente para esta edición"
            )

        if solicitud_previa:
            solicitud_previa.url_documento = carta_url
            solicitud_previa.estado = "pendiente"
            solicitud_previa.fecha_entrega = date.today()
            solicitud_previa.fecha_revision = None
            solicitud_previa.observaciones = None
            if requisito:
                solicitud_previa.id_requisito = requisito.id_requisito
                solicitud_previa.tipo_documento = requisito.nombre
            db.commit()
            db.refresh(solicitud_previa)
            return solicitud_previa

        solicitud = SolicitudIncorporacion(
            id_detalle_programa_alumno=existente_dpa.id_detalle_programa_alumno,
            id_alumno=alumno_id,
            id_programa_version_edicion=data.id_programa_version_edicion,
            id_requisito=data.id_requisito if requisito else None,
            tipo_documento=requisito.nombre if requisito else "Carta de Solicitud de Incorporación",
            estado="pendiente",
            url_documento=carta_url,
        )
        db.add(solicitud)
        db.commit()
        db.refresh(solicitud)
        return solicitud

    solicitudes_previas = db.query(SolicitudIncorporacion).filter(
        SolicitudIncorporacion.id_alumno == alumno_id,
        SolicitudIncorporacion.id_programa_version_edicion == data.id_programa_version_edicion,
        SolicitudIncorporacion.estado == "pendiente",
    ).first()
    if solicitudes_previas:
        raise HTTPException(
            status_code=400,
            detail="Ya tenés una solicitud de incorporación pendiente para esta edición"
        )

    if not data.id_modalidad_academica:
        raise HTTPException(status_code=400, detail="Se requiere modalidad académica para primera incorporación")

    _validar_modalidad_y_cupo(data, pv, alumno_id, db)

    descuento_aplicado = 0.0
    if data.id_tipo_descuento:
        from routers.detalle_programa_alumno import _validar_descuento
        td = _validar_descuento(data.id_tipo_descuento, data.id_modalidad_academica, alumno_id, db)
        descuento_aplicado = td.porcentaje

    modulo_inicio = data.modulo_inicio if data.modulo_inicio >= 1 else 1

    nuevo = DetalleProgramaAlumno(
        id_programa_version_edicion=data.id_programa_version_edicion,
        id_alumno=alumno_id,
        id_modalidad_academica=data.id_modalidad_academica,
        id_tipo_descuento=data.id_tipo_descuento,
        descuento_aplicado=descuento_aplicado,
        modulo_inicio=modulo_inicio,
        estado="postulante",
        es_incorporacion=True,
        fecha_inscripcion=date.today(),
    )
    db.add(nuevo)
    db.flush()

    from routers.detalle_programa_alumno import generar_control_documentacion, generar_control_descuento
    generar_control_documentacion(nuevo.id_detalle_programa_alumno, data.id_modalidad_academica, db)
    if data.id_tipo_descuento:
        generar_control_descuento(nuevo.id_detalle_programa_alumno, data.id_modalidad_academica, data.id_tipo_descuento, db)

    solicitud = SolicitudIncorporacion(
        id_detalle_programa_alumno=nuevo.id_detalle_programa_alumno,
        id_alumno=alumno_id,
        id_programa_version_edicion=data.id_programa_version_edicion,
        id_requisito=data.id_requisito if requisito else None,
        tipo_documento=requisito.nombre if requisito else "Carta de Solicitud de Incorporación",
        estado="pendiente",
        url_documento=carta_url,
    )
    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)
    return solicitud


def _solicitar_migracion(alumno_id, carta_url, requisito, data, db):
    dpa_activo = db.query(DetalleProgramaAlumno).join(
        ProgramaVersionEdicion,
        DetalleProgramaAlumno.id_programa_version_edicion == ProgramaVersionEdicion.id_programa_version_edicion
    ).filter(
        DetalleProgramaAlumno.id_alumno == alumno_id,
        DetalleProgramaAlumno.estado.in_({"postulante", "observado", "inscrito"}),
    ).first()
    if dpa_activo:
        raise HTTPException(
            status_code=400,
            detail="Tenés una inscripción activa en otra edición. Retirate o esperá a que termine para solicitar migración."
        )

    solicitud_pendiente = db.query(SolicitudIncorporacion).filter(
        SolicitudIncorporacion.id_alumno == alumno_id,
        SolicitudIncorporacion.id_programa_version_edicion.is_(None),
        SolicitudIncorporacion.estado == "pendiente",
    ).first()
    if solicitud_pendiente:
        raise HTTPException(
            status_code=400,
            detail="Ya tenés una solicitud de migración pendiente"
        )

    solicitud = SolicitudIncorporacion(
        id_alumno=alumno_id,
        id_requisito=data.id_requisito if requisito else None,
        tipo_documento=requisito.nombre if requisito else "Carta de Solicitud de Incorporación",
        estado="pendiente",
        url_documento=carta_url,
    )
    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)
    return solicitud


def _validar_modalidad_y_cupo(data, pv, alumno_id, db):
    if not data.id_modalidad_academica:
        raise HTTPException(status_code=400, detail="Se requiere modalidad académica")

    from models.modalidad_academica import ModalidadAcademica
    modalidad = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.id_modalidad_academica == data.id_modalidad_academica
    ).first()
    if not modalidad or modalidad.estado != "activo":
        raise HTTPException(status_code=400, detail="Modalidad académica no encontrada o inactiva")

    from routers.detalle_programa_alumno import validar_modalidad_programa, _validar_cupo
    validar_modalidad_programa(data.id_modalidad_academica, data.id_programa_version_edicion, db)
    _validar_cupo(data.id_programa_version_edicion, db)


@router.get("/", response_model=list[SolicitudIncorporacionConDetalle])
def listar_solicitudes(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    estado: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.ver")),
):
    query = db.query(SolicitudIncorporacion)

    if estado:
        query = query.filter(SolicitudIncorporacion.estado == estado)

    total = query.count()
    offset = (page - 1) * per_page
    solicitudes = query.order_by(SolicitudIncorporacion.id_solicitud.desc()).offset(offset).limit(per_page).all()

    alumno_ids = {s.id_alumno for s in solicitudes if s.id_alumno}
    pve_ids = {s.id_programa_version_edicion for s in solicitudes if s.id_programa_version_edicion}
    requisito_ids = {s.id_requisito for s in solicitudes if s.id_requisito}

    alumnos_map = {
        a.id_alumno: a
        for a in db.query(Alumno).filter(Alumno.id_alumno.in_(alumno_ids)).all()
    } if alumno_ids else {}

    pves = db.query(ProgramaVersionEdicion).options(
        joinedload(ProgramaVersionEdicion.programa_version)
            .joinedload(ProgramaVersion.programa)
    ).filter(
        ProgramaVersionEdicion.id_programa_version_edicion.in_(pve_ids)
    ).all() if pve_ids else []
    pve_map = {p.id_programa_version_edicion: p for p in pves}

    requisitos_map = {
        r.id_requisito: r
        for r in db.query(Requisito).filter(Requisito.id_requisito.in_(requisito_ids)).all()
    } if requisito_ids else {}

    items = []
    for s in solicitudes:
        alumno = alumnos_map.get(s.id_alumno) if s.id_alumno else None
        pve = pve_map.get(s.id_programa_version_edicion) if s.id_programa_version_edicion else None
        pv = pve.programa_version if pve else None
        prog = pv.programa if pv else None
        requisito = requisitos_map.get(s.id_requisito) if s.id_requisito else None

        dpa_estado = None
        if s.id_detalle_programa_alumno:
            dpa = db.query(DetalleProgramaAlumno).filter(
                DetalleProgramaAlumno.id_detalle_programa_alumno == s.id_detalle_programa_alumno
            ).first()
            dpa_estado = dpa.estado if dpa else None

        items.append(SolicitudIncorporacionConDetalle(
            id_solicitud=s.id_solicitud,
            tipo_documento=s.tipo_documento,
            estado=s.estado,
            url_documento=s.url_documento,
            observaciones=s.observaciones,
            fecha_entrega=s.fecha_entrega,
            fecha_revision=s.fecha_revision,
            created_at=s.created_at,
            id_alumno=s.id_alumno,
            alumno_nombre=alumno.nombre if alumno else None,
            alumno_apellido=alumno.apellido if alumno else None,
            alumno_ci=alumno.ci if alumno else None,
            id_programa_version_edicion=s.id_programa_version_edicion,
            edicion_numero=pve.edicion if pve else None,
            edicion_anio=pve.anio if pve else None,
            edicion_semestre=pve.semestre if pve else None,
            programa_nombre=prog.nombre_programa if prog else None,
            id_requisito=s.id_requisito,
            requisito_nombre=requisito.nombre if requisito else None,
            id_detalle_programa_alumno=s.id_detalle_programa_alumno,
            dpa_estado=dpa_estado,
            es_migracion=not s.id_programa_version_edicion,
        ))

    return items


@router.get("/mis-solicitudes", response_model=list[SolicitudIncorporacionResponse])
def mis_solicitudes(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    return db.query(SolicitudIncorporacion).filter(
        SolicitudIncorporacion.id_alumno == current_user.id_profile
    ).order_by(SolicitudIncorporacion.id_solicitud.desc()).all()


@router.get("/{id_solicitud}", response_model=SolicitudIncorporacionConDetalle)
def obtener_solicitud(
    id_solicitud: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    solicitud = db.query(SolicitudIncorporacion).filter(
        SolicitudIncorporacion.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    tiene_permiso_alumnos_ver = any(p.codigo == 'alumnos.ver' for p in current_user.permisos)
    if not tiene_permiso_alumnos_ver:
        if current_user.rol == 'alumno' and solicitud.id_alumno != current_user.id_profile:
            raise HTTPException(status_code=403, detail="No autorizado para ver esta solicitud")
        elif current_user.rol != 'alumno':
            raise HTTPException(status_code=403, detail="No autorizado para ver esta solicitud")

    alumno = None
    if solicitud.id_alumno:
        alumno = db.query(Alumno).filter(Alumno.id_alumno == solicitud.id_alumno).first()

    pve = None
    pv = None
    prog = None
    if solicitud.id_programa_version_edicion:
        pve = db.query(ProgramaVersionEdicion).options(
            joinedload(ProgramaVersionEdicion.programa_version)
                .joinedload(ProgramaVersion.programa)
        ).filter(
            ProgramaVersionEdicion.id_programa_version_edicion == solicitud.id_programa_version_edicion
        ).first()
        if pve:
            pv = pve.programa_version
            prog = pv.programa if pv else None

    requisito = None
    if solicitud.id_requisito:
        requisito = db.query(Requisito).filter(Requisito.id_requisito == solicitud.id_requisito).first()

    dpa_estado = None
    if solicitud.id_detalle_programa_alumno:
        dpa = db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == solicitud.id_detalle_programa_alumno
        ).first()
        dpa_estado = dpa.estado if dpa else None

    return SolicitudIncorporacionConDetalle(
        id_solicitud=solicitud.id_solicitud,
        tipo_documento=solicitud.tipo_documento,
        estado=solicitud.estado,
        url_documento=solicitud.url_documento,
        observaciones=solicitud.observaciones,
        fecha_entrega=solicitud.fecha_entrega,
        fecha_revision=solicitud.fecha_revision,
        created_at=solicitud.created_at,
        id_alumno=solicitud.id_alumno,
        alumno_nombre=alumno.nombre if alumno else None,
        alumno_apellido=alumno.apellido if alumno else None,
        alumno_ci=alumno.ci if alumno else None,
        id_programa_version_edicion=solicitud.id_programa_version_edicion,
        edicion_numero=pve.edicion if pve else None,
        edicion_anio=pve.anio if pve else None,
        edicion_semestre=pve.semestre if pve else None,
        programa_nombre=prog.nombre_programa if prog else None,
        id_requisito=solicitud.id_requisito,
        requisito_nombre=requisito.nombre if requisito else None,
        id_detalle_programa_alumno=solicitud.id_detalle_programa_alumno,
        dpa_estado=dpa_estado,
        es_migracion=not solicitud.id_programa_version_edicion,
    )


@router.patch("/{id_solicitud}/aprobar", response_model=SolicitudIncorporacionResponse)
def aprobar_solicitud(
    id_solicitud: int,
    data: AprobarSolicitudRequest = Body(default=AprobarSolicitudRequest()),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    solicitud = db.query(SolicitudIncorporacion).filter(
        SolicitudIncorporacion.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "pendiente":
        raise HTTPException(
            status_code=400,
            detail=f"La solicitud ya fue {solicitud.estado}"
        )

    if solicitud.id_detalle_programa_alumno:
        dpa = db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == solicitud.id_detalle_programa_alumno
        ).first()
        if dpa:
            dpa.estado = "postulante"
    else:
        if not data.id_programa_version_edicion or not data.id_modalidad_academica:
            raise HTTPException(
                status_code=400,
                detail="Para aprobar una solicitud de migración se requiere id_programa_version_edicion e id_modalidad_academica"
            )

        pve = db.query(ProgramaVersionEdicion).filter(
            ProgramaVersionEdicion.id_programa_version_edicion == data.id_programa_version_edicion
        ).first()
        if not pve:
            raise HTTPException(status_code=404, detail="Edición destino no encontrada")

        pv = pve.programa_version
        _validar_modalidad_y_cupo(
            type('obj', (object,), {
                'id_programa_version_edicion': data.id_programa_version_edicion,
                'id_modalidad_academica': data.id_modalidad_academica,
            })(),
            pv, solicitud.id_alumno, db
        )

        descuento_aplicado = 0.0
        if data.id_tipo_descuento:
            from routers.detalle_programa_alumno import _validar_descuento
            td = _validar_descuento(data.id_tipo_descuento, data.id_modalidad_academica, solicitud.id_alumno, db)
            descuento_aplicado = td.porcentaje

        modulo_inicio = data.modulo_inicio if data.modulo_inicio >= 1 else 1

        nuevo = DetalleProgramaAlumno(
            id_programa_version_edicion=data.id_programa_version_edicion,
            id_alumno=solicitud.id_alumno,
            id_modalidad_academica=data.id_modalidad_academica,
            id_tipo_descuento=data.id_tipo_descuento,
            descuento_aplicado=descuento_aplicado,
            modulo_inicio=modulo_inicio,
            estado="inscrito",
            es_incorporacion=True,
            fecha_inscripcion=date.today(),
        )
        db.add(nuevo)
        db.flush()

        solicitud.id_detalle_programa_alumno = nuevo.id_detalle_programa_alumno
        solicitud.id_programa_version_edicion = data.id_programa_version_edicion

        from routers.detalle_programa_alumno import generar_control_documentacion, generar_control_descuento
        generar_control_documentacion(nuevo.id_detalle_programa_alumno, data.id_modalidad_academica, db)
        if data.id_tipo_descuento:
            generar_control_descuento(nuevo.id_detalle_programa_alumno, data.id_modalidad_academica, data.id_tipo_descuento, db)

    solicitud.estado = "aceptado"
    solicitud.fecha_revision = date.today()
    db.commit()
    db.refresh(solicitud)
    return solicitud


@router.patch("/{id_solicitud}/rechazar", response_model=SolicitudIncorporacionResponse)
def rechazar_solicitud(
    id_solicitud: int,
    observaciones: str = "",
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    solicitud = db.query(SolicitudIncorporacion).filter(
        SolicitudIncorporacion.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "pendiente":
        raise HTTPException(
            status_code=400,
            detail=f"La solicitud ya fue {solicitud.estado}"
        )

    solicitud.estado = "rechazado"
    solicitud.fecha_revision = date.today()
    solicitud.observaciones = observaciones
    db.commit()
    db.refresh(solicitud)
    return solicitud
