from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sql_func
import math
from database import get_db
from dependencies import get_current_user, require_permiso
from models.solicitud_incorporacion import SolicitudIncorporacion, SolicitudDocumento
from models.solicitud_requisito import SolicitudRequisito
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.programa_version_edicion import ProgramaVersionEdicion
from models.programa_version import ProgramaVersion
from models.programa import Programa
from models.alumno import Alumno
from models.requisito import Requisito
from models.control_documentacion import ControlDocumentacion
from models.historial_inscripcion import HistorialInscripcion
from schemas.solicitud_incorporacion import (
    SolicitudIncorporacionCreate,
    AprobarSolicitudRequest,
    SolicitudIncorporacionResponse,
    SolicitudIncorporacionConDetalle,
    SolicitudDocumentoResponse,
)
from schemas.auth import UserResponse
from routers.utils import guardar_documento_base64, eliminar_foto, inferir_tipo_movimiento

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

    carta_url = guardar_documento_base64(data.url_documento, "incorporacion") if data.url_documento else ""

    if es_migracion:
        return _solicitar_migracion(alumno_id, carta_url, data, db)
    else:
        return _solicitar_primera_incorporacion(alumno_id, carta_url, data, db)


@router.get("/puede-migrar")
def puede_migrar(
    id_detalle_programa_alumno: int = Query(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    dpa = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id_detalle_programa_alumno,
        DetalleProgramaAlumno.id_alumno == current_user.id_profile,
    ).first()
    if not dpa:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    pve = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == dpa.id_programa_version_edicion
    ).first()
    if not pve:
        raise HTTPException(status_code=404, detail="Edición no encontrada")

    if pve.estado not in ("finalizado", "reprogramado"):
        return {"puede": False, "motivo": "La edición aún está en curso"}

    if dpa.estado in ("postulante", "observado"):
        return {"puede": False, "motivo": "Tu inscripción aún no está activa"}

    if dpa.estado == "retirado":
        return {"puede": False, "motivo": "Estás retirado. Solicitá reincorporación en su lugar."}

    pv = pve.programa_version
    dpa_activo = db.query(DetalleProgramaAlumno).join(
        ProgramaVersionEdicion,
        DetalleProgramaAlumno.id_programa_version_edicion == ProgramaVersionEdicion.id_programa_version_edicion,
    ).filter(
        DetalleProgramaAlumno.id_alumno == current_user.id_profile,
        ProgramaVersionEdicion.id_programa_version == pv.id_programa_version,
        DetalleProgramaAlumno.estado.in_({"postulante", "observado", "inscrito"}),
        DetalleProgramaAlumno.id_detalle_programa_alumno != dpa.id_detalle_programa_alumno,
    ).first()
    if dpa_activo:
        return {"puede": False, "motivo": "Ya tenés una inscripción activa en otra edición de este programa"}

    solicitud_pendiente = db.query(SolicitudIncorporacion).filter(
        SolicitudIncorporacion.id_programa_version_edicion.is_(None),
        SolicitudIncorporacion.estado == "pendiente",
    ).join(
        DetalleProgramaAlumno
    ).filter(
        DetalleProgramaAlumno.id_alumno == current_user.id_profile,
    ).first()
    if solicitud_pendiente:
        return {"puede": False, "motivo": "Ya tenés una solicitud de migración pendiente"}

    return {"puede": True, "motivo": None}
    configs = db.query(SolicitudRequisito).filter(
        SolicitudRequisito.estado == "activo",
        SolicitudRequisito.tipo == tipo,
    ).all()

    if not configs:
        requisito_default = db.query(Requisito).filter(Requisito.id_requisito == 6).first()
        if requisito_default:
            doc = SolicitudDocumento(
                id_solicitud=solicitud_id,
                id_requisito=6,
                url_documento=carta_url,
                estado="pendiente",
            )
            db.add(doc)
        return

    for cfg in configs:
        url = carta_url if cfg.id_requisito == 6 else ""
        doc = SolicitudDocumento(
            id_solicitud=solicitud_id,
            id_requisito=cfg.id_requisito,
            url_documento=url if url else "",
            estado="pendiente",
        )
        db.add(doc)


def _sincronizar_documentos(solicitud, db, tipo="incorporacion"):
    configs = db.query(SolicitudRequisito).filter(
        SolicitudRequisito.estado == "activo",
        SolicitudRequisito.tipo == tipo,
    ).all()
    existing_ids = {d.id_requisito for d in solicitud.documentos}

    added = False
    for cfg in configs:
        if cfg.id_requisito not in existing_ids:
            db.add(SolicitudDocumento(
                id_solicitud=solicitud.id_solicitud,
                id_requisito=cfg.id_requisito,
                url_documento="",
                estado="pendiente",
            ))
            added = True
    if added:
        db.commit()
        db.expire(solicitud)


def _build_docs_response(documentos, db):
    req_ids = {d.id_requisito for d in documentos}
    requisitos = db.query(Requisito).filter(
        Requisito.id_requisito.in_(req_ids)
    ).all() if req_ids else []
    req_names = {r.id_requisito: r.nombre for r in requisitos}

    return [
        SolicitudDocumentoResponse(
            id_solicitud_documento=d.id_solicitud_documento,
            id_requisito=d.id_requisito,
            nombre_requisito=req_names.get(d.id_requisito, f"Requisito #{d.id_requisito}"),
            url_documento=d.url_documento,
            estado=d.estado,
            fecha_entrega=d.fecha_entrega,
        )
        for d in documentos
    ]


def _solicitar_primera_incorporacion(alumno_id, carta_url, data, db):
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
            solicitud_previa.estado = "pendiente"
            solicitud_previa.fecha_revision = None
            solicitud_previa.observaciones = None
            db.flush()

            for d in solicitud_previa.documentos:
                if d.estado != "pendiente":
                    d.estado = "pendiente"
            _crear_documentos_solicitud(solicitud_previa.id_solicitud, carta_url, db)
            db.commit()
            db.refresh(solicitud_previa)
            return solicitud_previa

        solicitud = SolicitudIncorporacion(
            id_detalle_programa_alumno=existente_dpa.id_detalle_programa_alumno,
            id_programa_version_edicion=data.id_programa_version_edicion,
            estado="pendiente",
        )
        db.add(solicitud)
        db.flush()

        _crear_documentos_solicitud(solicitud.id_solicitud, carta_url, db)
        db.commit()
        db.refresh(solicitud)
        return SolicitudIncorporacionResponse(
            id_solicitud=solicitud.id_solicitud,
            id_detalle_programa_alumno=solicitud.id_detalle_programa_alumno,
            id_programa_version_edicion=solicitud.id_programa_version_edicion,
            estado=solicitud.estado,
            observaciones=solicitud.observaciones,
            fecha_revision=solicitud.fecha_revision,
            created_at=solicitud.created_at,
            updated_at=solicitud.updated_at,
            documentos=_build_docs_response(solicitud.documentos, db),
        )

    solicitudes_previas = db.query(SolicitudIncorporacion).join(
        SolicitudDocumento
    ).join(
        DetalleProgramaAlumno
    ).filter(
        DetalleProgramaAlumno.id_alumno == alumno_id,
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
        id_programa_version_edicion=data.id_programa_version_edicion,
        estado="pendiente",
    )
    db.add(solicitud)
    db.flush()

    _crear_documentos_solicitud(solicitud.id_solicitud, carta_url, db)
    db.commit()
    db.refresh(solicitud)
    return SolicitudIncorporacionResponse(
        id_solicitud=solicitud.id_solicitud,
        id_detalle_programa_alumno=solicitud.id_detalle_programa_alumno,
        id_programa_version_edicion=solicitud.id_programa_version_edicion,
        estado=solicitud.estado,
        observaciones=solicitud.observaciones,
        fecha_revision=solicitud.fecha_revision,
        created_at=solicitud.created_at,
        updated_at=solicitud.updated_at,
        documentos=_build_docs_response(solicitud.documentos, db),
    )


def _solicitar_migracion(alumno_id, carta_url, data, db):
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
        SolicitudIncorporacion.id_programa_version_edicion.is_(None),
        SolicitudIncorporacion.estado == "pendiente",
    ).join(
        DetalleProgramaAlumno
    ).filter(
        DetalleProgramaAlumno.id_alumno == alumno_id,
    ).first()
    if solicitud_pendiente:
        raise HTTPException(
            status_code=400,
            detail="Ya tenés una solicitud de migración pendiente"
        )

    solicitud = SolicitudIncorporacion(
        id_programa_version_edicion=None,
        estado="pendiente",
    )
    db.add(solicitud)
    db.flush()

    _crear_documentos_solicitud(solicitud.id_solicitud, carta_url, db)
    db.commit()
    db.refresh(solicitud)
    return SolicitudIncorporacionResponse(
        id_solicitud=solicitud.id_solicitud,
        id_detalle_programa_alumno=solicitud.id_detalle_programa_alumno,
        id_programa_version_edicion=solicitud.id_programa_version_edicion,
        estado=solicitud.estado,
        observaciones=solicitud.observaciones,
        fecha_revision=solicitud.fecha_revision,
        created_at=solicitud.created_at,
        updated_at=solicitud.updated_at,
        documentos=_build_docs_response(solicitud.documentos, db),
    )


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


def _load_solicitudes_con_detalle(solicitudes, db):
    pve_ids = {s.id_programa_version_edicion for s in solicitudes if s.id_programa_version_edicion}
    dpa_ids = {s.id_detalle_programa_alumno for s in solicitudes if s.id_detalle_programa_alumno}

    pves = db.query(ProgramaVersionEdicion).options(
        joinedload(ProgramaVersionEdicion.programa_version)
            .joinedload(ProgramaVersion.programa)
    ).filter(
        ProgramaVersionEdicion.id_programa_version_edicion.in_(pve_ids)
    ).all() if pve_ids else []
    pve_map = {p.id_programa_version_edicion: p for p in pves}

    dpas = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno.in_(dpa_ids)
    ).all() if dpa_ids else []
    dpa_map = {d.id_detalle_programa_alumno: d for d in dpas}

    alumno_ids = {dpa.id_alumno for dpa in dpas if dpa.id_alumno}
    alumnos_map = {
        a.id_alumno: a
        for a in db.query(Alumno).filter(Alumno.id_alumno.in_(alumno_ids)).all()
    } if alumno_ids else {}

    items = []
    for s in solicitudes:
        dpa = dpa_map.get(s.id_detalle_programa_alumno) if s.id_detalle_programa_alumno else None
        alumno = alumnos_map.get(dpa.id_alumno) if dpa and dpa.id_alumno else None
        pve = pve_map.get(s.id_programa_version_edicion) if s.id_programa_version_edicion else None
        pv = pve.programa_version if pve else None
        prog = pv.programa if pv else None

        if s.estado == "pendiente":
            _sincronizar_documentos(s, db)

        docs_response = _build_docs_response(s.documentos, db)

        items.append(SolicitudIncorporacionConDetalle(
            id_solicitud=s.id_solicitud,
            estado=s.estado,
            observaciones=s.observaciones,
            fecha_revision=s.fecha_revision,
            created_at=s.created_at,
            id_alumno=dpa.id_alumno if dpa else None,
            alumno_nombre=alumno.nombre if alumno else None,
            alumno_apellido=alumno.apellido if alumno else None,
            alumno_ci=alumno.ci if alumno else None,
            id_programa_version_edicion=s.id_programa_version_edicion,
            edicion_numero=pve.edicion if pve else None,
            edicion_anio=pve.anio if pve else None,
            edicion_semestre=pve.semestre if pve else None,
            programa_nombre=prog.nombre_programa if prog else None,
            id_detalle_programa_alumno=s.id_detalle_programa_alumno,
            dpa_estado=dpa.estado if dpa else None,
            es_migracion=not s.id_programa_version_edicion,
            documentos=docs_response,
        ))

    return items


@router.get("/", response_model=list[SolicitudIncorporacionConDetalle])
def listar_solicitudes(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    estado: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.ver")),
):
    query = db.query(SolicitudIncorporacion).options(
        joinedload(SolicitudIncorporacion.documentos)
    )

    if estado:
        query = query.filter(SolicitudIncorporacion.estado == estado)

    total = query.count()
    offset = (page - 1) * per_page
    solicitudes = query.order_by(SolicitudIncorporacion.id_solicitud.desc()).offset(offset).limit(per_page).all()

    return _load_solicitudes_con_detalle(solicitudes, db)


@router.get("/mis-solicitudes", response_model=list[SolicitudIncorporacionResponse])
def mis_solicitudes(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    solicitudes = db.query(SolicitudIncorporacion).options(
        joinedload(SolicitudIncorporacion.documentos)
    ).join(
        DetalleProgramaAlumno
    ).filter(
        DetalleProgramaAlumno.id_alumno == current_user.id_profile
    ).order_by(SolicitudIncorporacion.id_solicitud.desc()).all()

    result = []
    for s in solicitudes:
        if s.estado == "pendiente":
            _sincronizar_documentos(s, db)
        result.append(SolicitudIncorporacionResponse(
            id_solicitud=s.id_solicitud,
            id_detalle_programa_alumno=s.id_detalle_programa_alumno,
            id_programa_version_edicion=s.id_programa_version_edicion,
            estado=s.estado,
            observaciones=s.observaciones,
            fecha_revision=s.fecha_revision,
            created_at=s.created_at,
            updated_at=s.updated_at,
            documentos=_build_docs_response(s.documentos, db),
        ))
    return result


@router.get("/{id_solicitud}", response_model=SolicitudIncorporacionConDetalle)
def obtener_solicitud(
    id_solicitud: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    solicitud = db.query(SolicitudIncorporacion).options(
        joinedload(SolicitudIncorporacion.documentos)
    ).filter(
        SolicitudIncorporacion.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    tiene_permiso_alumnos_ver = any(p.codigo == 'alumnos.ver' for p in current_user.permisos)
    dpa = None
    if solicitud.id_detalle_programa_alumno:
        dpa = db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == solicitud.id_detalle_programa_alumno
        ).first()

    if not tiene_permiso_alumnos_ver:
        if current_user.rol == 'alumno':
            if not dpa or dpa.id_alumno != current_user.id_profile:
                raise HTTPException(status_code=403, detail="No autorizado para ver esta solicitud")
        else:
            raise HTTPException(status_code=403, detail="No autorizado para ver esta solicitud")

    alumno = None
    if dpa and dpa.id_alumno:
        alumno = db.query(Alumno).filter(Alumno.id_alumno == dpa.id_alumno).first()

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

    if solicitud.estado == "pendiente":
        _sincronizar_documentos(solicitud, db)

    docs_response = _build_docs_response(solicitud.documentos, db)

    return SolicitudIncorporacionConDetalle(
        id_solicitud=solicitud.id_solicitud,
        estado=solicitud.estado,
        observaciones=solicitud.observaciones,
        fecha_revision=solicitud.fecha_revision,
        created_at=solicitud.created_at,
        id_alumno=dpa.id_alumno if dpa else None,
        alumno_nombre=alumno.nombre if alumno else None,
        alumno_apellido=alumno.apellido if alumno else None,
        alumno_ci=alumno.ci if alumno else None,
        id_programa_version_edicion=solicitud.id_programa_version_edicion,
        edicion_numero=pve.edicion if pve else None,
        edicion_anio=pve.anio if pve else None,
        edicion_semestre=pve.semestre if pve else None,
        programa_nombre=prog.nombre_programa if prog else None,
        id_detalle_programa_alumno=solicitud.id_detalle_programa_alumno,
        dpa_estado=dpa.estado if dpa else None,
        es_migracion=not solicitud.id_programa_version_edicion,
        documentos=docs_response,
    )


@router.patch("/{id_solicitud}/aprobar", response_model=SolicitudIncorporacionConDetalle)
def aprobar_solicitud(
    id_solicitud: int,
    data: AprobarSolicitudRequest = Body(default=AprobarSolicitudRequest()),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    solicitud = db.query(SolicitudIncorporacion).options(
        joinedload(SolicitudIncorporacion.documentos)
    ).filter(
        SolicitudIncorporacion.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "pendiente":
        raise HTTPException(
            status_code=400,
            detail=f"La solicitud ya fue {solicitud.estado}"
        )

    dpa = None
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
            pv, None, db
        )

        descuento_aplicado = 0.0
        if data.id_tipo_descuento:
            from routers.detalle_programa_alumno import _validar_descuento
            td = _validar_descuento(data.id_tipo_descuento, data.id_modalidad_academica, None, db)
            descuento_aplicado = td.porcentaje

        modulo_inicio = data.modulo_inicio if data.modulo_inicio >= 1 else 1

        alumno_id = None
        if dpa:
            alumno_id = dpa.id_alumno

        dpa_origen = None
        if alumno_id:
            pve_origen_candidate = db.query(ProgramaVersionEdicion).filter(
                ProgramaVersionEdicion.id_programa_version == pv.id_programa_version
            ).all()
            pve_ids_origen = [p.id_programa_version_edicion for p in pve_origen_candidate]
            if pve_ids_origen:
                dpa_origen = db.query(DetalleProgramaAlumno).filter(
                    DetalleProgramaAlumno.id_alumno == alumno_id,
                    DetalleProgramaAlumno.id_programa_version_edicion.in_(pve_ids_origen),
                    DetalleProgramaAlumno.id_detalle_programa_alumno != (dpa.id_detalle_programa_alumno if dpa else -1),
                    DetalleProgramaAlumno.estado.notin_(["retirado"]),
                ).order_by(DetalleProgramaAlumno.id_detalle_programa_alumno.desc()).first()

        if dpa_origen:
            pve_origen = db.query(ProgramaVersionEdicion).filter(
                ProgramaVersionEdicion.id_programa_version_edicion == dpa_origen.id_programa_version_edicion
            ).first()
            if pve_origen:
                destino_antes = (
                    pve.anio < pve_origen.anio or
                    (pve.anio == pve_origen.anio and pve.semestre < pve_origen.semestre) or
                    (pve.anio == pve_origen.anio and pve.semestre == pve_origen.semestre and pve.edicion < pve_origen.edicion)
                )
                if destino_antes:
                    raise HTTPException(
                        status_code=400,
                        detail=f"La edición destino (Ed. {pve.edicion}) es anterior a la edición de origen (Ed. {pve_origen.edicion}). No se puede volver a una edición anterior."
                    )

        nuevo = DetalleProgramaAlumno(
            id_programa_version_edicion=data.id_programa_version_edicion,
            id_alumno=alumno_id,
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

        if dpa_origen:
            historial = HistorialInscripcion(
                id_detalle_origen=dpa_origen.id_detalle_programa_alumno,
                id_detalle_destino=nuevo.id_detalle_programa_alumno,
                id_solicitud=solicitud.id_solicitud,
                tipo_movimiento=inferir_tipo_movimiento(dpa_origen, nuevo, db),
                motivo=data.motivo or None,
            )
            db.add(historial)

        solicitud.id_detalle_programa_alumno = nuevo.id_detalle_programa_alumno
        solicitud.id_programa_version_edicion = data.id_programa_version_edicion

        from routers.detalle_programa_alumno import generar_control_documentacion, generar_control_descuento
        generar_control_documentacion(nuevo.id_detalle_programa_alumno, data.id_modalidad_academica, db)
        if data.id_tipo_descuento:
            generar_control_descuento(nuevo.id_detalle_programa_alumno, data.id_modalidad_academica, data.id_tipo_descuento, db)

    for doc in solicitud.documentos:
        doc.estado = "aceptado"

    if solicitud.id_detalle_programa_alumno:
        for doc in solicitud.documentos:
            if not doc.url_documento:
                continue
            control = db.query(ControlDocumentacion).filter(
                ControlDocumentacion.id_detalle_programa_alumno == solicitud.id_detalle_programa_alumno,
                ControlDocumentacion.id_requisito == doc.id_requisito,
            ).first()
            if control:
                control.url_documento = doc.url_documento
                control.estado = "aceptado"
                control.fecha_entrega = date.today()
            else:
                db.add(ControlDocumentacion(
                    id_detalle_programa_alumno=solicitud.id_detalle_programa_alumno,
                    id_requisito=doc.id_requisito,
                    url_documento=doc.url_documento,
                    obligatorio=True,
                    estado="aceptado",
                    fecha_entrega=date.today(),
                ))

    solicitud.estado = "aceptado"
    solicitud.fecha_revision = date.today()
    db.commit()
    db.refresh(solicitud)

    items = _load_solicitudes_con_detalle([solicitud], db)
    return items[0]


@router.get("/{id_solicitud}/preview-migracion")
def preview_migracion(
    id_solicitud: int,
    id_programa_version_edicion: int = Query(...),
    id_modalidad_academica: int = Query(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    from models.nota import Nota
    from models.pago import Pago
    from models.modalidad_academica import ModalidadAcademica
    from models.detalle_programa_modulo import DetalleProgramaModulo
    from models.modulo import Modulo
    from schemas.enums import clasificar_nota

    solicitud = db.query(SolicitudIncorporacion).options(
        joinedload(SolicitudIncorporacion.documentos)
    ).filter(
        SolicitudIncorporacion.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "pendiente":
        raise HTTPException(status_code=400, detail="Solo se puede previsualizar solicitudes pendientes")

    dpa_origen = None
    if solicitud.id_detalle_programa_alumno:
        dpa_origen = db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == solicitud.id_detalle_programa_alumno
        ).first()

    if not dpa_origen:
        raise HTTPException(status_code=400, detail="No se encontró la inscripción origen del alumno")

    alumno = db.query(Alumno).filter(Alumno.id_alumno == dpa_origen.id_alumno).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    pve_origen = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == dpa_origen.id_programa_version_edicion
    ).first()

    pv_origen = pve_origen.programa_version if pve_origen else None
    prog_origen = pv_origen.programa if pv_origen else None

    notas_origen = db.query(Nota).filter(
        Nota.id_detalle_programa_alumno == dpa_origen.id_detalle_programa_alumno
    ).all()

    dpm_ids_origen = {n.id_detalle_programa_modulo for n in notas_origen}
    dpms_origen = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo.in_(dpm_ids_origen)
    ).all() if dpm_ids_origen else []
    dpm_origen_map = {dpm.id_detalle_programa_modulo: dpm for dpm in dpms_origen}

    modulos_origen_ids = {dpm.id_modulo for dpm in dpms_origen}
    modulos_origen = db.query(Modulo).filter(
        Modulo.id_modulo.in_(modulos_origen_ids)
    ).all() if modulos_origen_ids else []
    modulo_origen_map = {m.id_modulo: m for m in modulos_origen}

    nota_by_dpm: dict[int, Nota] = {}
    for n in notas_origen:
        existing = nota_by_dpm.get(n.id_detalle_programa_modulo)
        if not existing or n.id_nota > existing.id_nota:
            nota_by_dpm[n.id_detalle_programa_modulo] = n

    notas_preview = []
    for dpm in dpms_origen:
        mod = modulo_origen_map.get(dpm.id_modulo)
        nota_obj = nota_by_dpm.get(dpm.id_detalle_programa_modulo)
        if nota_obj and mod:
            nota_val = float(nota_obj.nota)
            notas_preview.append({
                "modulo_nombre": mod.nombre_modulo,
                "modulo_orden": dpm.orden,
                "nota": nota_val,
                "calificacion": clasificar_nota(nota_val).value if nota_val is not None else None,
            })
    notas_preview.sort(key=lambda x: x["modulo_orden"])

    pagos_origen = db.query(Pago).filter(
        Pago.id_detalle_programa_alumno == dpa_origen.id_detalle_programa_alumno
    ).all()

    pagos_preview = []
    for p in pagos_origen:
        pagos_preview.append({
            "concepto": p.concepto,
            "monto": float(p.monto),
            "estado": p.estado,
            "fecha_pago": str(p.fecha_pago),
        })

    pve_destino = db.query(ProgramaVersionEdicion).options(
        joinedload(ProgramaVersionEdicion.programa_version)
            .joinedload(ProgramaVersion.programa)
    ).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id_programa_version_edicion
    ).first()
    if not pve_destino:
        raise HTTPException(status_code=404, detail="Edición destino no encontrada")

    pv_destino = pve_destino.programa_version if pve_destino else None
    prog_destino = pv_destino.programa if pv_destino else None

    if pv_origen and pv_destino and pv_origen.id_programa_version != pv_destino.id_programa_version:
        raise HTTPException(status_code=400, detail="La edición destino debe pertenecer al mismo programa")

    modalidad = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.id_modalidad_academica == id_modalidad_academica
    ).first()
    if not modalidad or modalidad.estado != "activo":
        raise HTTPException(status_code=400, detail="Modalidad académica no encontrada o inactiva")

    dpms_destino = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == id_programa_version_edicion
    ).order_by(DetalleProgramaModulo.orden).all()

    modulos_destino_ids = {dpm.id_modulo for dpm in dpms_destino}
    modulos_destino = db.query(Modulo).filter(
        Modulo.id_modulo.in_(modulos_destino_ids)
    ).all() if modulos_destino_ids else []
    modulo_destino_map = {m.id_modulo: m for m in modulos_destino}

    nombres_origen = {modulo_origen_map.get(dpm.id_modulo).nombre_modulo.lower()
                      for dpm in dpms_origen
                      if modulo_origen_map.get(dpm.id_modulo)}

    modulos_destino_preview = []
    for dpm in dpms_destino:
        mod = modulo_destino_map.get(dpm.id_modulo)
        nombre = mod.nombre_modulo if mod else f"Módulo #{dpm.id_modulo}"
        modulos_destino_preview.append({
            "modulo_nombre": nombre,
            "modulo_orden": dpm.orden,
            "match": nombre.lower() in nombres_origen,
        })

    from routers.detalle_programa_alumno import _validar_cupo
    cupo_disponible = None
    try:
        cupo_disponible = pve_destino.cupo_maximo - db.query(sql_func.count(
            DetalleProgramaAlumno.id_detalle_programa_alumno
        )).filter(
            DetalleProgramaAlumno.id_programa_version_edicion == id_programa_version_edicion,
            DetalleProgramaAlumno.estado.notin_(["retirado", "observado"]),
        ).scalar()
    except Exception:
        pass

    modalidades_pve = []
    try:
        from models.modalidad_tipo_programa import ModalidadTipoPrograma
        mtp_list = db.query(ModalidadTipoPrograma).filter(
            ModalidadTipoPrograma.id_tipo_programa == pv_destino.programa.id_tipo_programa
        ).all() if pv_destino and pv_destino.programa else []
        ma_ids = [mtp.id_modalidad_academica for mtp in mtp_list]
        if ma_ids:
            mas = db.query(ModalidadAcademica).filter(
                ModalidadAcademica.id_modalidad_academica.in_(ma_ids),
                ModalidadAcademica.estado == "activo",
            ).all()
            modalidades_pve = [{"id": m.id_modalidad_academica, "nombre": m.nombre_modalidad} for m in mas]
    except Exception:
        pass

    notas_match_count = sum(1 for mp in modulos_destino_preview if mp["match"])

    return {
        "alumno": {
            "id_alumno": alumno.id_alumno,
            "nombre": alumno.nombre,
            "apellido": alumno.apellido,
            "ci": alumno.ci,
        },
        "origen": {
            "id_detalle_programa_alumno": dpa_origen.id_detalle_programa_alumno,
            "edicion_numero": pve_origen.edicion if pve_origen else None,
            "edicion_anio": pve_origen.anio if pve_origen else None,
            "edicion_semestre": pve_origen.semestre if pve_origen else None,
            "notas": notas_preview,
            "pagos": pagos_preview,
            "total_notas": len(notas_preview),
            "total_pagos": len(pagos_preview),
            "monto_total_pagos": sum(float(p.monto) for p in pagos_origen if p.estado == "aprobado"),
        },
        "destino": {
            "id_programa_version_edicion": pve_destino.id_programa_version_edicion,
            "edicion_numero": pve_destino.edicion,
            "edicion_anio": pve_destino.anio,
            "edicion_semestre": pve_destino.semestre,
            "modulos": modulos_destino_preview,
            "precio": pve_destino.precio,
            "cupo_disponible": cupo_disponible,
            "modalidades": modalidades_pve,
        },
        "resumen": {
            "notas_a_migrar": notas_match_count,
            "pagos_a_migrar": len(pagos_preview),
            "monto_a_migrar": sum(float(p.monto) for p in pagos_origen if p.estado == "aprobado"),
        },
    }


class SubirDocumentoSolicitud(BaseModel):
    url_documento: str


@router.patch("/{id_solicitud}/documentos/{id_doc}/subir", response_model=SolicitudIncorporacionResponse)
def subir_documento_solicitud(
    id_solicitud: int,
    id_doc: int,
    data: SubirDocumentoSolicitud = Body(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    solicitud = db.query(SolicitudIncorporacion).options(
        joinedload(SolicitudIncorporacion.documentos)
    ).filter(
        SolicitudIncorporacion.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "pendiente":
        raise HTTPException(status_code=400, detail="Solo se pueden subir documentos a solicitudes pendientes")

    doc = next((d for d in solicitud.documentos if d.id_solicitud_documento == id_doc), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado en esta solicitud")

    url = guardar_documento_base64(data.url_documento, "incorporacion")
    doc.url_documento = url
    doc.fecha_entrega = date.today()
    db.commit()
    db.refresh(solicitud)

    return SolicitudIncorporacionResponse(
        id_solicitud=solicitud.id_solicitud,
        id_detalle_programa_alumno=solicitud.id_detalle_programa_alumno,
        id_programa_version_edicion=solicitud.id_programa_version_edicion,
        estado=solicitud.estado,
        observaciones=solicitud.observaciones,
        fecha_revision=solicitud.fecha_revision,
        created_at=solicitud.created_at,
        updated_at=solicitud.updated_at,
        documentos=_build_docs_response(solicitud.documentos, db),
    )


@router.patch("/{id_solicitud}/rechazar", response_model=SolicitudIncorporacionConDetalle)
def rechazar_solicitud(
    id_solicitud: int,
    observaciones: str = "",
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    solicitud = db.query(SolicitudIncorporacion).options(
        joinedload(SolicitudIncorporacion.documentos)
    ).filter(
        SolicitudIncorporacion.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "pendiente":
        raise HTTPException(
            status_code=400,
            detail=f"La solicitud ya fue {solicitud.estado}"
        )

    for doc in solicitud.documentos:
        if doc.estado == "pendiente":
            doc.estado = "rechazado"

    solicitud.estado = "rechazado"
    solicitud.fecha_revision = date.today()
    solicitud.observaciones = observaciones
    db.commit()
    db.refresh(solicitud)

    items = _load_solicitudes_con_detalle([solicitud], db)
    return items[0]
