from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sql_func
from database import get_db
from dependencies import get_current_user, require_permiso
from models.solicitud import Solicitud
from models.tipo_solicitud import TipoSolicitud
from models.solicitud_incorporacion import SolicitudIncorporacion
from models.solicitud_migracion import SolicitudMigracion
from models.documento_solicitud import DocumentoSolicitud
from models.solicitud_requisito import SolicitudRequisito
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.programa_version_edicion import ProgramaVersionEdicion
from models.programa_version import ProgramaVersion
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.alumno import Alumno
from models.requisito import Requisito
from models.control_documentacion import ControlDocumentacion
from models.historial_inscripcion import HistorialInscripcion
from schemas.solicitud import (
    SolicitudCreate,
    AprobarSolicitudRequest,
    SolicitudResponse,
    SolicitudConDetalle,
    SolicitudIncorporacionResponse,
    SolicitudMigracionResponse,
    DocumentoSolicitudResponse,
    ModuloPendiente,
    ModuloCoincidencia,
    DestinoRecomendado,
    DestinosRecomendadosResponse,
)
from schemas.auth import UserResponse
from routers.utils import guardar_documento_base64, inferir_tipo_movimiento, resolver_modulo_inicio

router = APIRouter(
    prefix="/solicitud",
    tags=["Solicitudes"],
    dependencies=[Depends(get_current_user)],
)


def _build_docs_response(documentos, db):
    req_ids = {d.id_requisito for d in documentos}
    requisitos = db.query(Requisito).filter(
        Requisito.id_requisito.in_(req_ids)
    ).all() if req_ids else []
    req_names = {r.id_requisito: r.nombre for r in requisitos}

    return [
        DocumentoSolicitudResponse(
            id_solicitud_documento=d.id_solicitud_documento,
            id_requisito=d.id_requisito,
            nombre_requisito=req_names.get(d.id_requisito, f"Requisito #{d.id_requisito}"),
            url_documento=d.url_documento,
            estado=d.estado,
            fecha_entrega=d.fecha_entrega,
        )
        for d in documentos
    ]


def _crear_documentos(solicitud_id, id_tipo_solicitud, carta_url, db):
    configs = db.query(SolicitudRequisito).filter(
        SolicitudRequisito.estado == "activo",
        SolicitudRequisito.id_tipo_solicitud == id_tipo_solicitud,
    ).all()

    if not configs:
        requisito_default = db.query(Requisito).filter(Requisito.id_requisito == 6).first()
        if requisito_default:
            doc = DocumentoSolicitud(
                id_solicitud=solicitud_id,
                id_requisito=6,
                url_documento=carta_url,
                estado="pendiente",
            )
            db.add(doc)
        return

    for cfg in configs:
        url = carta_url if cfg.id_requisito == 6 else ""
        doc = DocumentoSolicitud(
            id_solicitud=solicitud_id,
            id_requisito=cfg.id_requisito,
            url_documento=url if url else "",
            estado="pendiente",
        )
        db.add(doc)


def _determinar_tipo(alumno_id, id_pve_edicion, db):
    if not id_pve_edicion:
        dpa_origen = db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_alumno == alumno_id,
            DetalleProgramaAlumno.estado.in_(["finalizado", "incorporado", "inscrito"]),
        ).order_by(DetalleProgramaAlumno.id_detalle_programa_alumno.desc()).first()
        if dpa_origen:
            return ("migracion", dpa_origen.id_detalle_programa_alumno)
        dpa_retirado = db.query(DetalleProgramaAlumno).join(
            ProgramaVersionEdicion,
        ).filter(
            DetalleProgramaAlumno.id_alumno == alumno_id,
            DetalleProgramaAlumno.estado == "retirado",
            ProgramaVersionEdicion.estado == "finalizado",
        ).order_by(DetalleProgramaAlumno.id_detalle_programa_alumno.desc()).first()
        if dpa_retirado:
            return ("migracion", dpa_retirado.id_detalle_programa_alumno)
        return ("migracion", None)

    pve = db.query(ProgramaVersionEdicion).get(id_pve_edicion)
    if not pve:
        raise HTTPException(status_code=404, detail="Edición no encontrada")

    dpa_retirado = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_alumno == alumno_id,
        DetalleProgramaAlumno.id_programa_version_edicion == id_pve_edicion,
        DetalleProgramaAlumno.estado == "retirado",
    ).first()
    if dpa_retirado:
        return ("reincorporacion", dpa_retirado.id_detalle_programa_alumno)

    dpa_existente = db.query(DetalleProgramaAlumno).join(
        ProgramaVersionEdicion,
    ).filter(
        DetalleProgramaAlumno.id_alumno == alumno_id,
        ProgramaVersionEdicion.id_programa_version == pve.id_programa_version,
        DetalleProgramaAlumno.id_programa_version_edicion != id_pve_edicion,
        DetalleProgramaAlumno.estado != "retirado",
    ).first()
    if dpa_existente:
        return ("migracion", dpa_existente.id_detalle_programa_alumno)

    return ("incorporacion", None)


def _pve_from_solicitud(solicitud):
    pve_id = None
    if solicitud.incorporacion:
        pve_id = solicitud.incorporacion.id_programa_version_edicion
    elif solicitud.migracion:
        pve_id = solicitud.migracion.id_edicion_destino
    return pve_id


def _load_con_detalle(solicitudes, db):
    pve_ids = set()
    dpa_ids = set()
    alumno_ids = set()

    for s in solicitudes:
        if s.incorporacion:
            pve_ids.add(s.incorporacion.id_programa_version_edicion)
        if s.migracion:
            pve_ids.add(s.migracion.id_edicion_destino)
        if s.id_detalle_origen:
            dpa_ids.add(s.id_detalle_origen)
        alumno_ids.add(s.id_alumno)

    dpas = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno.in_(dpa_ids)
    ).all() if dpa_ids else []
    dpa_map = {d.id_detalle_programa_alumno: d for d in dpas}

    for d in dpas:
        pve_ids.add(d.id_programa_version_edicion)

    pves = db.query(ProgramaVersionEdicion).options(
        joinedload(ProgramaVersionEdicion.programa_version).joinedload(ProgramaVersion.programa)
    ).filter(
        ProgramaVersionEdicion.id_programa_version_edicion.in_(pve_ids)
    ).all() if pve_ids else []
    pve_map = {p.id_programa_version_edicion: p for p in pves}

    alumnos_map = {
        a.id_alumno: a
        for a in db.query(Alumno).filter(Alumno.id_alumno.in_(alumno_ids)).all()
    } if alumno_ids else {}

    items = []
    for s in solicitudes:
        dpa = dpa_map.get(s.id_detalle_origen) if s.id_detalle_origen else None
        alumno = alumnos_map.get(s.id_alumno)
        pve_id = _pve_from_solicitud(s)
        if not pve_id and dpa:
            pve_id = dpa.id_programa_version_edicion
        pve = pve_map.get(pve_id) if pve_id else None
        pv = pve.programa_version if pve else None
        prog = pv.programa if pv else None

        items.append(SolicitudConDetalle(
            id_solicitud=s.id_solicitud,
            id_tipo_solicitud=s.id_tipo_solicitud,
            tipo_codigo=db.query(TipoSolicitud.codigo).filter(
                TipoSolicitud.id_tipo_solicitud == s.id_tipo_solicitud
            ).scalar() or "",
            id_alumno=s.id_alumno,
            alumno_nombre=alumno.nombre if alumno else None,
            alumno_apellido=alumno.apellido if alumno else None,
            alumno_ci=alumno.ci if alumno else None,
            estado=s.estado,
            motivo=s.motivo,
            motivo_rechazo=s.motivo_rechazo,
            id_detalle_origen=s.id_detalle_origen,
            edicion_numero=pve.edicion if pve else None,
            edicion_anio=pve.anio if pve else None,
            edicion_semestre=pve.semestre if pve else None,
            programa_nombre=prog.nombre_programa if prog else None,
            dpa_estado=dpa.estado if dpa else None,
            dpa_modulo_inicio=dpa.modulo_inicio if dpa else None,
            dpa_id_modulo_inicio=dpa.id_modulo_inicio if dpa else None,
            created_at=s.created_at,
            documentos=_build_docs_response(s.documentos, db),
            incorporacion=SolicitudIncorporacionResponse.model_validate(s.incorporacion) if s.incorporacion else None,
            migracion=SolicitudMigracionResponse.model_validate(s.migracion) if s.migracion else None,
        ))

    return items


@router.post("/solicitar", response_model=SolicitudResponse, status_code=201)
def solicitar(
    data: SolicitudCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    alumno_id = current_user.id_profile
    tipo_codigo, id_origen = _determinar_tipo(alumno_id, data.id_programa_version_edicion, db)

    tipo = db.query(TipoSolicitud).filter(TipoSolicitud.codigo == tipo_codigo).first()
    if not tipo:
        raise HTTPException(status_code=400, detail=f"Tipo de solicitud inválido: {tipo_codigo}")

    if tipo_codigo == "incorporacion":
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
        if not data.id_modalidad_academica:
            raise HTTPException(status_code=400, detail="Se requiere modalidad académica")

        pv = pve.programa_version
        inscripcion_activa = db.query(DetalleProgramaAlumno).join(
            ProgramaVersionEdicion,
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

        pendiente = db.query(Solicitud).join(TipoSolicitud).join(
            SolicitudIncorporacion
        ).filter(
            Solicitud.id_alumno == alumno_id,
            TipoSolicitud.codigo == "incorporacion",
            Solicitud.estado == "pendiente",
            SolicitudIncorporacion.id_programa_version_edicion == data.id_programa_version_edicion,
        ).first()
        if pendiente:
            raise HTTPException(
                status_code=400,
                detail="Ya tenés una solicitud de incorporación pendiente para esta edición"
            )

    elif tipo_codigo == "migracion":
        pendiente = db.query(Solicitud).join(TipoSolicitud).filter(
            Solicitud.id_alumno == alumno_id,
            TipoSolicitud.codigo == "migracion",
            Solicitud.estado == "pendiente",
        ).first()
        if pendiente:
            raise HTTPException(
                status_code=400,
                detail="Ya tenés una solicitud de migración pendiente"
            )

        dpa_activo = db.query(DetalleProgramaAlumno).join(
            ProgramaVersionEdicion,
        ).filter(
            DetalleProgramaAlumno.id_alumno == alumno_id,
            DetalleProgramaAlumno.estado.in_({"postulante", "observado", "inscrito"}),
        ).first()
        if dpa_activo:
            raise HTTPException(
                status_code=400,
                detail="Tenés una inscripción activa en otra edición. Retirate o esperá a que termine."
            )

    elif tipo_codigo == "reincorporacion":
        if not id_origen:
            raise HTTPException(status_code=400, detail="No se encontró inscripción para reincorporar")

        dpa = db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == id_origen,
            DetalleProgramaAlumno.id_alumno == alumno_id,
            DetalleProgramaAlumno.estado == "retirado",
        ).first()
        if not dpa:
            raise HTTPException(status_code=400, detail="La inscripción no está en estado retirado")

        pve = db.query(ProgramaVersionEdicion).filter(
            ProgramaVersionEdicion.id_programa_version_edicion == dpa.id_programa_version_edicion
        ).first()
        if not pve or pve.estado not in ("en_curso", "reprogramado"):
            raise HTTPException(
                status_code=400,
                detail="La edición ya no está activa. Solicitá migración en su lugar."
            )

        pendiente = db.query(Solicitud).join(TipoSolicitud).filter(
            Solicitud.id_detalle_origen == id_origen,
            TipoSolicitud.codigo == "reincorporacion",
            Solicitud.estado == "pendiente",
        ).first()
        if pendiente:
            raise HTTPException(
                status_code=400,
                detail="Ya tenés una solicitud de reincorporación pendiente para esta inscripción"
            )

    carta_url = guardar_documento_base64(data.url_documento, "solicitudes") if data.url_documento else ""

    solicitud = Solicitud(
        id_tipo_solicitud=tipo.id_tipo_solicitud,
        id_alumno=alumno_id,
        id_detalle_origen=id_origen,
        estado="pendiente",
        motivo=data.motivo,
    )
    db.add(solicitud)
    db.flush()

    if tipo_codigo == "incorporacion":
        incorporacion = SolicitudIncorporacion(
            id_solicitud=solicitud.id_solicitud,
            id_programa_version_edicion=data.id_programa_version_edicion,
            id_modalidad_academica=data.id_modalidad_academica,
            id_tipo_descuento=data.id_tipo_descuento,
        )
        db.add(incorporacion)

    _crear_documentos(solicitud.id_solicitud, tipo.id_tipo_solicitud, carta_url, db)
    db.commit()
    db.refresh(solicitud)

    return SolicitudResponse(
        id_solicitud=solicitud.id_solicitud,
        id_tipo_solicitud=solicitud.id_tipo_solicitud,
        tipo_codigo=tipo_codigo,
        id_alumno=solicitud.id_alumno,
        id_detalle_origen=solicitud.id_detalle_origen,
        estado=solicitud.estado,
        motivo=solicitud.motivo,
        motivo_rechazo=solicitud.motivo_rechazo,
        created_at=solicitud.created_at,
        updated_at=solicitud.updated_at,
        documentos=_build_docs_response(solicitud.documentos, db),
        incorporacion=SolicitudIncorporacionResponse.model_validate(solicitud.incorporacion) if solicitud.incorporacion else None,
        migracion=SolicitudMigracionResponse.model_validate(solicitud.migracion) if solicitud.migracion else None,
    )


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

    if dpa.estado == "retirado" and pve.estado == "reprogramado":
        return {"puede": False, "motivo": "Estás retirado. Solicitá reincorporación en su lugar."}

    pv = pve.programa_version
    dpa_activo = db.query(DetalleProgramaAlumno).join(
        ProgramaVersionEdicion,
    ).filter(
        DetalleProgramaAlumno.id_alumno == current_user.id_profile,
        ProgramaVersionEdicion.id_programa_version == pv.id_programa_version,
        DetalleProgramaAlumno.estado.in_({"postulante", "observado", "inscrito"}),
        DetalleProgramaAlumno.id_detalle_programa_alumno != dpa.id_detalle_programa_alumno,
    ).first()
    if dpa_activo:
        return {"puede": False, "motivo": "Ya tenés una inscripción activa en otra edición de este programa"}

    solicitud_pendiente = db.query(Solicitud).join(TipoSolicitud).filter(
        Solicitud.id_alumno == current_user.id_profile,
        TipoSolicitud.codigo == "migracion",
        Solicitud.estado == "pendiente",
    ).first()
    if solicitud_pendiente:
        return {"puede": False, "motivo": "Ya tenés una solicitud de migración pendiente"}

    return {"puede": True, "motivo": None}


@router.get("/", response_model=list[SolicitudConDetalle])
def listar(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    estado: str | None = None,
    tipo: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.ver")),
):
    query = db.query(Solicitud).options(
        joinedload(Solicitud.documentos),
        joinedload(Solicitud.incorporacion),
        joinedload(Solicitud.migracion),
    )

    if estado:
        query = query.filter(Solicitud.estado == estado)
    if tipo:
        query = query.join(TipoSolicitud).filter(TipoSolicitud.codigo == tipo)

    offset = (page - 1) * per_page
    solicitudes = query.order_by(Solicitud.id_solicitud.desc()).offset(offset).limit(per_page).all()
    return _load_con_detalle(solicitudes, db)


@router.get("/pendientes-count")
def contar_pendientes(
    tipo: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.ver")),
):
    query = db.query(Solicitud).filter(Solicitud.estado == "pendiente")
    if tipo:
        query = query.join(TipoSolicitud).filter(TipoSolicitud.codigo == tipo)
    return {"count": query.count()}


@router.get("/mis-solicitudes", response_model=list[SolicitudResponse])
def mis_solicitudes(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    solicitudes = db.query(Solicitud).options(
        joinedload(Solicitud.documentos),
        joinedload(Solicitud.tipo),
        joinedload(Solicitud.incorporacion),
        joinedload(Solicitud.migracion),
    ).filter(
        Solicitud.id_alumno == current_user.id_profile,
    ).order_by(Solicitud.id_solicitud.desc()).all()

    result = []
    for s in solicitudes:
        result.append(SolicitudResponse(
            id_solicitud=s.id_solicitud,
            id_tipo_solicitud=s.id_tipo_solicitud,
            tipo_codigo=s.tipo.codigo,
            id_alumno=s.id_alumno,
            id_detalle_origen=s.id_detalle_origen,
            estado=s.estado,
            motivo=s.motivo,
            motivo_rechazo=s.motivo_rechazo,
            created_at=s.created_at,
            updated_at=s.updated_at,
            documentos=_build_docs_response(s.documentos, db),
            incorporacion=SolicitudIncorporacionResponse.model_validate(s.incorporacion) if s.incorporacion else None,
            migracion=SolicitudMigracionResponse.model_validate(s.migracion) if s.migracion else None,
        ))
    return result


@router.get("/{id_solicitud}", response_model=SolicitudConDetalle)
def obtener(
    id_solicitud: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    solicitud = db.query(Solicitud).options(
        joinedload(Solicitud.documentos),
        joinedload(Solicitud.incorporacion),
        joinedload(Solicitud.migracion),
    ).filter(
        Solicitud.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    tiene_permiso = any(p.codigo == 'alumnos.ver' for p in current_user.permisos)
    if not tiene_permiso:
        if current_user.rol != 'alumno' or solicitud.id_alumno != current_user.id_profile:
            raise HTTPException(status_code=403, detail="No autorizado")

    return _load_con_detalle([solicitud], db)[0]


@router.patch("/{id_solicitud}/aprobar", response_model=SolicitudConDetalle)
def aprobar(
    id_solicitud: int,
    data: AprobarSolicitudRequest = Body(default=AprobarSolicitudRequest()),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    solicitud = db.query(Solicitud).options(
        joinedload(Solicitud.documentos),
        joinedload(Solicitud.tipo),
        joinedload(Solicitud.incorporacion),
        joinedload(Solicitud.migracion),
    ).filter(
        Solicitud.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "pendiente":
        raise HTTPException(
            status_code=400,
            detail=f"La solicitud ya fue {solicitud.estado}"
        )

    tipo_codigo = solicitud.tipo.codigo

    if tipo_codigo == "incorporacion":
        inc = solicitud.incorporacion
        if not inc:
            raise HTTPException(status_code=400, detail="Faltan datos de incorporación en la solicitud")

        pve = db.query(ProgramaVersionEdicion).filter(
            ProgramaVersionEdicion.id_programa_version_edicion == inc.id_programa_version_edicion
        ).first()
        if not pve:
            raise HTTPException(status_code=404, detail="Edición no encontrada")

        pv = pve.programa_version
        from routers.detalle_programa_alumno import _validar_cupo, validar_modalidad_programa

        validar_modalidad_programa(inc.id_modalidad_academica, pve.id_programa_version_edicion, db)
        _validar_cupo(pve.id_programa_version_edicion, db)

        descuento_aplicado = 0.0
        if inc.id_tipo_descuento:
            from routers.detalle_programa_alumno import _validar_descuento
            td = _validar_descuento(inc.id_tipo_descuento, inc.id_modalidad_academica, solicitud.id_alumno, db)
            descuento_aplicado = td.porcentaje

        id_mod, mod_orden = resolver_modulo_inicio(
            inc.id_programa_version_edicion, data.id_modulo_inicio, db
        )

        nuevo = DetalleProgramaAlumno(
            id_programa_version_edicion=inc.id_programa_version_edicion,
            id_alumno=solicitud.id_alumno,
            id_modalidad_academica=inc.id_modalidad_academica,
            id_tipo_descuento=inc.id_tipo_descuento,
            descuento_aplicado=descuento_aplicado,
            id_modulo_inicio=id_mod,
            modulo_inicio=mod_orden,
            estado="postulante",
            es_incorporacion=True,
            fecha_inscripcion=date.today(),
        )
        db.add(nuevo)
        db.flush()

        solicitud.id_detalle_origen = nuevo.id_detalle_programa_alumno

        historial = HistorialInscripcion(
            id_detalle_origen=nuevo.id_detalle_programa_alumno,
            id_detalle_destino=nuevo.id_detalle_programa_alumno,
            id_solicitud=solicitud.id_solicitud,
            tipo_movimiento="incorporacion",
            motivo=None,
        )
        db.add(historial)

        from routers.detalle_programa_alumno import generar_control_documentacion, generar_control_descuento
        generar_control_documentacion(nuevo.id_detalle_programa_alumno, inc.id_modalidad_academica, db)
        if inc.id_tipo_descuento:
            generar_control_descuento(nuevo.id_detalle_programa_alumno, inc.id_modalidad_academica,
                                       inc.id_tipo_descuento, db)

    elif tipo_codigo == "migracion":
        if not data.id_programa_version_edicion:
            raise HTTPException(
                status_code=400,
                detail="Para aprobar una migración se requiere id_programa_version_edicion"
            )

        pve_destino = db.query(ProgramaVersionEdicion).filter(
            ProgramaVersionEdicion.id_programa_version_edicion == data.id_programa_version_edicion
        ).first()
        if not pve_destino:
            raise HTTPException(status_code=404, detail="Edición destino no encontrada")

        pv = pve_destino.programa_version
        from routers.detalle_programa_alumno import _validar_cupo

        dpa_origen = None
        if solicitud.id_detalle_origen:
            dpa_origen = db.query(DetalleProgramaAlumno).filter(
                DetalleProgramaAlumno.id_detalle_programa_alumno == solicitud.id_detalle_origen
            ).first()
        else:
            pve_ids_origen = [
                p.id_programa_version_edicion
                for p in db.query(ProgramaVersionEdicion).filter(
                    ProgramaVersionEdicion.id_programa_version == pv.id_programa_version
                ).all()
            ]
            if pve_ids_origen:
                dpa_origen = db.query(DetalleProgramaAlumno).filter(
                    DetalleProgramaAlumno.id_alumno == solicitud.id_alumno,
                    DetalleProgramaAlumno.id_programa_version_edicion.in_(pve_ids_origen),
                    DetalleProgramaAlumno.estado.notin_(["retirado"]),
                ).order_by(DetalleProgramaAlumno.id_detalle_programa_alumno.desc()).first()

        if not dpa_origen:
            raise HTTPException(status_code=400, detail="No se encontró la inscripción origen")

        pve_origen = db.query(ProgramaVersionEdicion).filter(
            ProgramaVersionEdicion.id_programa_version_edicion == dpa_origen.id_programa_version_edicion
        ).first()
        if pve_origen:
            destino_antes = (
                pve_destino.anio < pve_origen.anio or
                (pve_destino.anio == pve_origen.anio and pve_destino.semestre < pve_origen.semestre) or
                (pve_destino.anio == pve_origen.anio and pve_destino.semestre == pve_origen.semestre and pve_destino.edicion < pve_origen.edicion)
            )
            if destino_antes:
                raise HTTPException(
                    status_code=400,
                    detail="La edición destino es anterior a la edición de origen. No se puede volver a una edición anterior."
                )

        modalidad_heredada = dpa_origen.id_modalidad_academica
        _validar_cupo(data.id_programa_version_edicion, db)

        descuento_aplicado = 0.0
        if data.id_tipo_descuento:
            from routers.detalle_programa_alumno import _validar_descuento
            td = _validar_descuento(data.id_tipo_descuento, modalidad_heredada, None, db)
            descuento_aplicado = td.porcentaje

        id_mod, mod_orden = resolver_modulo_inicio(
            data.id_programa_version_edicion, data.id_modulo_inicio, db
        )

        nuevo = DetalleProgramaAlumno(
            id_programa_version_edicion=data.id_programa_version_edicion,
            id_alumno=solicitud.id_alumno,
            id_modalidad_academica=modalidad_heredada,
            id_tipo_descuento=data.id_tipo_descuento,
            descuento_aplicado=descuento_aplicado,
            id_modulo_inicio=id_mod,
            modulo_inicio=mod_orden,
            estado="inscrito",
            es_incorporacion=True,
            fecha_inscripcion=date.today(),
        )
        db.add(nuevo)
        db.flush()

        migracion = SolicitudMigracion(
            id_solicitud=solicitud.id_solicitud,
            id_edicion_destino=data.id_programa_version_edicion,
            motivo=data.motivo or "",
        )
        db.add(migracion)

        historial = HistorialInscripcion(
            id_detalle_origen=dpa_origen.id_detalle_programa_alumno,
            id_detalle_destino=nuevo.id_detalle_programa_alumno,
            id_solicitud=solicitud.id_solicitud,
            tipo_movimiento=inferir_tipo_movimiento(dpa_origen, nuevo, db),
            motivo=data.motivo or "",
        )
        db.add(historial)

        solicitud.id_detalle_origen = nuevo.id_detalle_programa_alumno

        from routers.detalle_programa_alumno import generar_control_documentacion, generar_control_descuento
        generar_control_documentacion(nuevo.id_detalle_programa_alumno, modalidad_heredada, db)
        if data.id_tipo_descuento:
            generar_control_descuento(nuevo.id_detalle_programa_alumno, modalidad_heredada, data.id_tipo_descuento, db)

    elif tipo_codigo == "reincorporacion":
        dpa = None
        if solicitud.id_detalle_origen:
            dpa = db.query(DetalleProgramaAlumno).filter(
                DetalleProgramaAlumno.id_detalle_programa_alumno == solicitud.id_detalle_origen
            ).first()

        if not dpa:
            raise HTTPException(status_code=404, detail="Inscripción no encontrada")

        if dpa.estado != "retirado":
            raise HTTPException(
                status_code=400,
                detail=f"La inscripción está en estado '{dpa.estado}', se esperaba 'retirado'"
            )

        pve = dpa.programa_version_edicion
        if not pve or pve.estado not in ("en_curso", "reprogramado"):
            raise HTTPException(
                status_code=400,
                detail="La edición ya no está activa. No se puede aprobar reincorporación."
            )

        if data.id_modulo_inicio:
            id_mod, mod_orden = resolver_modulo_inicio(
                dpa.id_programa_version_edicion, data.id_modulo_inicio, db
            )
            dpa.id_modulo_inicio = id_mod
            dpa.modulo_inicio = mod_orden

        dpa.estado = "inscrito"

        historial = HistorialInscripcion(
            id_detalle_origen=dpa.id_detalle_programa_alumno,
            id_detalle_destino=dpa.id_detalle_programa_alumno,
            id_solicitud=solicitud.id_solicitud,
            tipo_movimiento=inferir_tipo_movimiento(dpa, dpa, db),
            motivo=solicitud.motivo,
        )
        db.add(historial)

    for doc in solicitud.documentos:
        doc.estado = "aceptado"

    if solicitud.id_detalle_origen:
        for doc in solicitud.documentos:
            if not doc.url_documento:
                continue
            control = db.query(ControlDocumentacion).filter(
                ControlDocumentacion.id_detalle_programa_alumno == solicitud.id_detalle_origen,
                ControlDocumentacion.id_requisito == doc.id_requisito,
            ).first()
            if control:
                control.url_documento = doc.url_documento
                control.estado = "aceptado"
                control.fecha_entrega = date.today()
            else:
                db.add(ControlDocumentacion(
                    id_detalle_programa_alumno=solicitud.id_detalle_origen,
                    id_requisito=doc.id_requisito,
                    url_documento=doc.url_documento,
                    obligatorio=True,
                    estado="aceptado",
                    fecha_entrega=date.today(),
                ))

    solicitud.estado = "aprobado"
    db.commit()
    db.refresh(solicitud)

    items = _load_con_detalle([solicitud], db)
    return items[0]


@router.patch("/{id_solicitud}/rechazar", response_model=SolicitudConDetalle)
def rechazar(
    id_solicitud: int,
    motivo_rechazo: str = Body(""),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    solicitud = db.query(Solicitud).options(
        joinedload(Solicitud.documentos),
    ).filter(
        Solicitud.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "pendiente":
        raise HTTPException(
            status_code=400,
            detail=f"La solicitud ya fue {solicitud.estado}"
        )

    for doc in solicitud.documentos:
        if doc.estado in ("pendiente", "entregado"):
            doc.estado = "rechazado"

    solicitud.estado = "rechazado"
    solicitud.motivo_rechazo = motivo_rechazo or None
    db.commit()
    db.refresh(solicitud)

    items = _load_con_detalle([solicitud], db)
    return items[0]


@router.patch("/{id_solicitud}/documentos/{id_doc}/subir", response_model=SolicitudResponse)
def subir_documento(
    id_solicitud: int,
    id_doc: int,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    solicitud = db.query(Solicitud).options(
        joinedload(Solicitud.documentos),
        joinedload(Solicitud.incorporacion),
        joinedload(Solicitud.migracion),
    ).filter(
        Solicitud.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "pendiente":
        raise HTTPException(status_code=400, detail="Solo se pueden subir documentos a solicitudes pendientes")

    if solicitud.id_alumno != current_user.id_profile:
        raise HTTPException(status_code=403, detail="Esta solicitud no te pertenece")

    doc = next((d for d in solicitud.documentos if d.id_solicitud_documento == id_doc), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado en esta solicitud")

    url_documento = body.get("url_documento", "")
    if not url_documento:
        raise HTTPException(status_code=400, detail="Se requiere url_documento")

    url = guardar_documento_base64(url_documento, "solicitudes")
    doc.url_documento = url
    doc.estado = "entregado"
    doc.fecha_entrega = date.today()
    db.commit()
    db.refresh(solicitud)

    tipo_codigo = db.query(TipoSolicitud.codigo).filter(
        TipoSolicitud.id_tipo_solicitud == solicitud.id_tipo_solicitud
    ).scalar()

    return SolicitudResponse(
        id_solicitud=solicitud.id_solicitud,
        id_tipo_solicitud=solicitud.id_tipo_solicitud,
        tipo_codigo=tipo_codigo or "",
        id_alumno=solicitud.id_alumno,
        id_detalle_origen=solicitud.id_detalle_origen,
        estado=solicitud.estado,
        motivo=solicitud.motivo,
        motivo_rechazo=solicitud.motivo_rechazo,
        created_at=solicitud.created_at,
        updated_at=solicitud.updated_at,
        documentos=_build_docs_response(solicitud.documentos, db),
        incorporacion=SolicitudIncorporacionResponse.model_validate(solicitud.incorporacion) if solicitud.incorporacion else None,
        migracion=SolicitudMigracionResponse.model_validate(solicitud.migracion) if solicitud.migracion else None,
    )


@router.get("/{id_solicitud}/preview-migracion")
def preview_migracion(
    id_solicitud: int,
    id_programa_version_edicion: int = Query(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    from models.nota import Nota
    from models.pago import Pago
    from models.transaccion_pago import TransaccionPago
    from models.detalle_programa_modulo import DetalleProgramaModulo
    from models.modulo import Modulo
    from schemas.enums import clasificar_nota

    solicitud = db.query(Solicitud).options(
        joinedload(Solicitud.incorporacion),
        joinedload(Solicitud.migracion),
    ).filter(
        Solicitud.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "pendiente":
        raise HTTPException(status_code=400, detail="Solo se puede previsualizar solicitudes pendientes")

    dpa_origen = None
    if solicitud.id_detalle_origen:
        dpa_origen = db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == solicitud.id_detalle_origen
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

    notas_origen = db.query(Nota).filter(
        Nota.id_detalle_programa_alumno == dpa_origen.id_detalle_programa_alumno
    ).all()

    dpm_ids_origen = {n.id_detalle_programa_modulo for n in notas_origen}
    dpms_origen = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo.in_(dpm_ids_origen)
    ).all() if dpm_ids_origen else []

    modulos_origen_ids = {dpm.id_modulo for dpm in dpms_origen}
    modulos_origen = db.query(Modulo).filter(
        Modulo.id_modulo.in_(modulos_origen_ids)
    ).all() if modulos_origen_ids else []
    modulo_origen_map = {m.id_modulo: m for m in modulos_origen}

    nota_by_dpm = {}
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

    pagos_origen = db.query(Pago, TransaccionPago).join(
        TransaccionPago, TransaccionPago.id_transaccion == Pago.id_transaccion
    ).filter(
        TransaccionPago.id_detalle_programa_alumno == dpa_origen.id_detalle_programa_alumno
    ).all()

    pagos_preview = [
        {"concepto": p.concepto, "monto": float(p.monto), "estado": t.estado, "fecha_pago": str(t.fecha_pago)}
        for p, t in pagos_origen
    ]

    pve_destino = db.query(ProgramaVersionEdicion).options(
        joinedload(ProgramaVersionEdicion.programa_version).joinedload(ProgramaVersion.programa)
    ).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id_programa_version_edicion
    ).first()
    if not pve_destino:
        raise HTTPException(status_code=404, detail="Edición destino no encontrada")

    pv_destino = pve_destino.programa_version if pve_destino else None
    if pv_origen and pv_destino and pv_origen.id_programa_version != pv_destino.id_programa_version:
        raise HTTPException(status_code=400, detail="La edición destino debe pertenecer al mismo programa")

    dpms_destino = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == id_programa_version_edicion
    ).order_by(DetalleProgramaModulo.orden).all()

    modulos_destino_ids = {dpm.id_modulo for dpm in dpms_destino}
    modulos_destino = db.query(Modulo).filter(
        Modulo.id_modulo.in_(modulos_destino_ids)
    ).all() if modulos_destino_ids else []
    modulo_destino_map = {m.id_modulo: m for m in modulos_destino}

    nombres_origen = {modulo_origen_map.get(dpm.id_modulo).nombre_modulo.lower()
                      for dpm in dpms_origen if modulo_origen_map.get(dpm.id_modulo)}

    modulos_destino_preview = []
    for dpm in dpms_destino:
        mod = modulo_destino_map.get(dpm.id_modulo)
        nombre = mod.nombre_modulo if mod else f"Módulo #{dpm.id_modulo}"
        modulos_destino_preview.append({
            "modulo_nombre": nombre,
            "modulo_orden": dpm.orden,
            "match": nombre.lower() in nombres_origen,
        })

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
            "monto_total_pagos": sum(float(p.monto) for p, t in pagos_origen if t.estado == "confirmado"),
        },
        "destino": {
            "id_programa_version_edicion": pve_destino.id_programa_version_edicion,
            "edicion_numero": pve_destino.edicion,
            "edicion_anio": pve_destino.anio,
            "edicion_semestre": pve_destino.semestre,
            "modulos": modulos_destino_preview,
            "precio": pve_destino.precio,
            "cupo_disponible": cupo_disponible,
        },
        "resumen": {
            "notas_a_migrar": notas_match_count,
            "pagos_a_migrar": len(pagos_preview),
            "monto_a_migrar": sum(float(p.monto) for p, t in pagos_origen if t.estado == "confirmado"),
        },
    }


def _motivo_destino(afinidad: int, aprovechables: int, total: int, coincidencias: list[ModuloCoincidencia]) -> str:
    if total == 0:
        return "El alumno no tiene módulos pendientes en la edición origen."
    base = f"Cubre {aprovechables} de {total} módulo(s) pendiente(s) ({afinidad}% de afinidad)."
    no_disp = [c.nombre_modulo for c in coincidencias if not c.disponible]
    if no_disp:
        base += " No aprovechables: " + "; ".join(no_disp) + "."
    return base


def _motivo_recomendado(destinos: list[DestinoRecomendado]) -> str:
    mejor = destinos[0]
    empatados = [
        d for d in destinos
        if d.aprovechables == mejor.aprovechables and d.afinidad_pct == mejor.afinidad_pct
    ]
    motivo = mejor.motivo_recomendacion
    if len(empatados) > 1:
        if mejor.cupo_disponible is not None and any(
            e.cupo_disponible is not None and e.cupo_disponible < mejor.cupo_disponible for e in empatados
        ):
            motivo += " Mejor cupo disponible entre las de igual afinidad."
        elif mejor.fecha_inicio is not None:
            motivo += " Mayor proximidad de inicio entre las de igual afinidad."
        else:
            motivo += " Mejor disponibilidad general."
    return motivo


@router.get("/{id_solicitud}/destinos-recomendados", response_model=DestinosRecomendadosResponse)
def destinos_recomendados(
    id_solicitud: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    from models.nota import Nota
    from models.modulo import Modulo
    from schemas.enums import clasificar_nota

    solicitud = db.query(Solicitud).options(
        joinedload(Solicitud.incorporacion),
        joinedload(Solicitud.migracion),
    ).filter(
        Solicitud.id_solicitud == id_solicitud
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "pendiente":
        raise HTTPException(status_code=400, detail="Solo se pueden evaluar solicitudes pendientes")

    tipo = db.query(TipoSolicitud).filter(
        TipoSolicitud.id_tipo_solicitud == solicitud.id_tipo_solicitud
    ).first()
    if not tipo or tipo.codigo != "migracion":
        raise HTTPException(status_code=400, detail="Solo aplica a solicitudes de migración")

    if not solicitud.id_detalle_origen:
        raise HTTPException(status_code=400, detail="No se encontró la inscripción origen del alumno")

    dpa_origen = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == solicitud.id_detalle_origen
    ).first()
    if not dpa_origen:
        raise HTTPException(status_code=400, detail="No se encontró la inscripción origen del alumno")

    alumno = db.query(Alumno).filter(Alumno.id_alumno == dpa_origen.id_alumno).first()

    pve_origen = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == dpa_origen.id_programa_version_edicion
    ).first()
    if not pve_origen or not pve_origen.id_programa_version:
        raise HTTPException(status_code=400, detail="No se encontró la edición origen del alumno")

    dpms_origen = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == pve_origen.id_programa_version_edicion
    ).order_by(DetalleProgramaModulo.orden).all()
    if not dpms_origen:
        raise HTTPException(status_code=400, detail="La edición origen no tiene módulos cargados")

    modulo_ids = {d.id_modulo for d in dpms_origen}
    modulos_map = {
        m.id_modulo: m
        for m in db.query(Modulo).filter(Modulo.id_modulo.in_(modulo_ids)).all()
    }

    notas_origen = db.query(Nota).filter(
        Nota.id_detalle_programa_alumno == dpa_origen.id_detalle_programa_alumno
    ).all()
    nota_by_dpm = {}
    for n in notas_origen:
        prev = nota_by_dpm.get(n.id_detalle_programa_modulo)
        if not prev or n.id_nota > prev.id_nota:
            nota_by_dpm[n.id_detalle_programa_modulo] = n

    APROBADAS = {"suficiente", "bueno", "distinguido", "sobresaliente"}
    aprobadas = set()
    for dpm_id, n in nota_by_dpm.items():
        try:
            if clasificar_nota(float(n.nota)).value in APROBADAS:
                aprobadas.add(dpm_id)
        except (TypeError, ValueError):
            continue

    modulo_inicio_snapshot = dpa_origen.modulo_inicio or 1

    pendientes = []
    for dpm in dpms_origen:
        if dpm.orden < modulo_inicio_snapshot:
            continue
        if dpm.id_detalle_programa_modulo in aprobadas:
            continue
        mod = modulos_map.get(dpm.id_modulo)
        pendientes.append(ModuloPendiente(
            id_modulo=dpm.id_modulo,
            nombre_modulo=mod.nombre_modulo if mod else f"Módulo #{dpm.id_modulo}",
            orden_origen=dpm.orden,
        ))

    dpas_alumno = db.query(DetalleProgramaAlumno.id_programa_version_edicion).filter(
        DetalleProgramaAlumno.id_alumno == dpa_origen.id_alumno,
    ).all()
    ediciones_alumno = {row[0] for row in dpas_alumno}

    candidatos = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version == pve_origen.id_programa_version,
        ProgramaVersionEdicion.es_historico == False,
        ProgramaVersionEdicion.estado.in_(["programado", "en_curso", "reprogramado"]),
        ProgramaVersionEdicion.id_programa_version_edicion != pve_origen.id_programa_version_edicion,
        ProgramaVersionEdicion.id_programa_version_edicion.notin_(ediciones_alumno),
    ).order_by(ProgramaVersionEdicion.fecha_inicio.asc().nullslast()).all()

    destinos = []
    for pve in candidatos:
        dpms_dest = db.query(DetalleProgramaModulo).filter(
            DetalleProgramaModulo.id_programa_version_edicion == pve.id_programa_version_edicion
        ).all()
        dpm_dest_map = {d.id_modulo: d for d in dpms_dest}

        coincidencias = []
        aprovechables = 0
        for p in pendientes:
            d_dest = dpm_dest_map.get(p.id_modulo)
            disponible = d_dest is not None and d_dest.estado != "finalizado"
            if disponible:
                aprovechables += 1
            coincidencias.append(ModuloCoincidencia(
                id_modulo=p.id_modulo,
                nombre_modulo=p.nombre_modulo,
                orden_origen=p.orden_origen,
                disponible=disponible,
                estado_destino=d_dest.estado if d_dest else None,
                posicion_destino=d_dest.orden if d_dest else None,
            ))

        total = len(pendientes)
        afinidad = round(100 * aprovechables / total) if total else 100

        cupo_ocupado = db.query(sql_func.count(DetalleProgramaAlumno.id_detalle_programa_alumno)).filter(
            DetalleProgramaAlumno.id_programa_version_edicion == pve.id_programa_version_edicion,
            DetalleProgramaAlumno.estado.notin_(["retirado", "observado"]),
        ).scalar() or 0
        cupo_disponible = (pve.cupo_maximo - cupo_ocupado) if pve.cupo_maximo is not None else None

        destinos.append(DestinoRecomendado(
            id_programa_version_edicion=pve.id_programa_version_edicion,
            edicion=pve.edicion,
            semestre=pve.semestre,
            anio=pve.anio,
            estado=pve.estado,
            modalidad=pve.modalidad,
            precio=float(pve.precio) if pve.precio is not None else None,
            cupo_maximo=pve.cupo_maximo,
            cupo_disponible=cupo_disponible,
            fecha_inicio=pve.fecha_inicio,
            afinidad_pct=afinidad,
            aprovechables=aprovechables,
            pendientes=total,
            coincidencias=coincidencias,
            recomendado=False,
            motivo_recomendacion=_motivo_destino(afinidad, aprovechables, total, coincidencias),
        ))

    destinos.sort(key=lambda d: (
        -d.aprovechables,
        -d.afinidad_pct,
        -(d.cupo_disponible if d.cupo_disponible is not None else -1),
        d.fecha_inicio is None,
        d.fecha_inicio or date.max,
        d.precio if d.precio is not None else float("inf"),
        d.id_programa_version_edicion,
    ))

    if destinos:
        destinos[0].recomendado = True
        destinos[0].motivo_recomendacion = _motivo_recomendado(destinos)

    return DestinosRecomendadosResponse(
        id_solicitud=solicitud.id_solicitud,
        id_alumno=dpa_origen.id_alumno,
        alumno_nombre=alumno.nombre if alumno else None,
        alumno_apellido=alumno.apellido if alumno else None,
        modulo_inicio_origen=modulo_inicio_snapshot,
        pendientes=pendientes,
        destinos=destinos,
    )
