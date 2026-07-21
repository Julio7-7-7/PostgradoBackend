from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sql_func
import math
from database import get_db
from dependencies import get_current_user, require_permiso
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.modalidad_academica import ModalidadAcademica
from models.tipo_descuento import TipoDescuento
from models.modalidad_tipo_descuento import ModalidadTipoDescuento
from models.modalidad_tipo_programa import ModalidadTipoPrograma
from models.programa_version_edicion import ProgramaVersionEdicion
from models.control_documentacion import ControlDocumentacion
from models.requisito import Requisito
from models.alumno import Alumno
from models.historial_inscripcion import HistorialInscripcion
from models.documento_incorporacion import DocumentoIncorporacion
from schemas.detalle_programa_alumno import (
    DetalleProgramaAlumnoCreate, DetalleProgramaAlumnoUpdate, DetalleProgramaAlumnoResponse,
    InscripcionEdicionItem, PaginatedInscripcionesResponse, AlumnoBasico,
    TransferirInscripcionRequest,
)
from schemas.admin import AutoInscribirRequest
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/detalle-programa-alumno",
    tags=["Detalle Programa Alumno"],
    dependencies=[Depends(get_current_user)]
)

TRANSICIONES_ESTADO = {
    "postulante": ["observado", "inscrito", "retirado"],
    "observado": ["inscrito", "postulante", "retirado"],
    "inscrito": ["incorporado", "finalizado", "retirado"],
    "incorporado": ["finalizado", "retirado"],
    "finalizado": ["graduado"],
    "graduado": [],
    "retirado": [],
}


def _validar_transicion_estado(estado_actual, nuevo_estado):
    opciones = TRANSICIONES_ESTADO.get(estado_actual, [])
    valor = nuevo_estado.value if hasattr(nuevo_estado, 'value') else nuevo_estado
    if valor not in opciones:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cambiar de '{estado_actual}' a '{valor}'"
        )


def _validar_cupo(id_programa_version_edicion, db: Session):
    pve = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id_programa_version_edicion
    ).first()
    if not pve:
        raise HTTPException(status_code=404, detail="Edición no encontrada")
    if pve.estado not in ("programado", "en_curso"):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede inscribir en una edición con estado '{pve.estado}'"
        )
    inscritos = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_programa_version_edicion == id_programa_version_edicion,
        DetalleProgramaAlumno.estado != "retirado",
    ).count()
    if inscritos >= pve.cupo_maximo:
        raise HTTPException(
            status_code=400,
            detail=f"No hay cupo disponible. Máximo: {pve.cupo_maximo}, inscritos: {inscritos}"
        )


def generar_control_documentacion(id_detalle: int, id_modalidad_academica: int, db: Session):
    from models.modalidad_requisito import ModalidadRequisito
    vinculos = db.query(ModalidadRequisito).filter(
        ModalidadRequisito.id_modalidad_academica == id_modalidad_academica,
    ).all()
    requisito_ids = [v.id_requisito for v in vinculos]
    if not requisito_ids:
        return
    requisitos = db.query(Requisito).filter(
        Requisito.id_requisito.in_(requisito_ids),
        Requisito.estado == "activo"
    ).all()
    for requisito in requisitos:
        control = ControlDocumentacion(
            id_detalle_programa_alumno=id_detalle,
            id_requisito=requisito.id_requisito,
            estado="pendiente",
            obligatorio=True
        )
        db.add(control)


def generar_control_descuento(id_detalle: int, id_modalidad_academica: int, id_tipo_descuento: int, db: Session):
    vinculo = db.query(ModalidadTipoDescuento).filter(
        ModalidadTipoDescuento.id_modalidad_academica == id_modalidad_academica,
        ModalidadTipoDescuento.id_tipo_descuento == id_tipo_descuento,
    ).first()
    if not vinculo:
        return

    tipo_desc = db.query(TipoDescuento).options(
        joinedload(TipoDescuento.requisitos)
    ).filter(
        TipoDescuento.id_tipo_descuento == id_tipo_descuento
    ).first()

    for requisito in tipo_desc.requisitos:
        existente = db.query(ControlDocumentacion).filter(
            ControlDocumentacion.id_detalle_programa_alumno == id_detalle,
            ControlDocumentacion.id_requisito == requisito.id_requisito,
        ).first()
        if existente:
            existente.obligatorio = True
        else:
            control = ControlDocumentacion(
                id_detalle_programa_alumno=id_detalle,
                id_requisito=requisito.id_requisito,
                estado="pendiente",
                obligatorio=True,
            )
            db.add(control)


def limpiar_control_descuento(id_detalle: int, id_tipo_descuento: int, db: Session):
    tipo_desc = db.query(TipoDescuento).options(
        joinedload(TipoDescuento.requisitos)
    ).filter(
        TipoDescuento.id_tipo_descuento == id_tipo_descuento
    ).first()
    if not tipo_desc:
        return
    requisito_ids = [r.id_requisito for r in tipo_desc.requisitos]
    if not requisito_ids:
        return
    controles = db.query(ControlDocumentacion).filter(
        ControlDocumentacion.id_detalle_programa_alumno == id_detalle,
        ControlDocumentacion.id_requisito.in_(requisito_ids),
    ).all()
    for ctrl in controles:
        ctrl.obligatorio = False


def validar_modalidad_programa(id_modalidad_academica: int, id_programa_version_edicion: int, db: Session):
    pv = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id_programa_version_edicion
    ).first()
    if not pv:
        raise HTTPException(status_code=404, detail="Edición no encontrada")

    id_tipo_programa = pv.programa_version.programa.id_tipo_programa

    vinculo = db.query(ModalidadTipoPrograma).filter(
        ModalidadTipoPrograma.id_modalidad_academica == id_modalidad_academica,
        ModalidadTipoPrograma.id_tipo_programa == id_tipo_programa,
    ).first()
    if not vinculo:
        modalidad = db.query(ModalidadAcademica).filter(
            ModalidadAcademica.id_modalidad_academica == id_modalidad_academica
        ).first()
        nombre_modalidad = modalidad.nombre_modalidad if modalidad else str(id_modalidad_academica)
        nombre_tipo = pv.programa_version.programa.tipo_programa.nombre
        raise HTTPException(
            status_code=400,
            detail=f"La modalidad '{nombre_modalidad}' no está permitida para el tipo de programa '{nombre_tipo}'"
        )


def _validar_descuento(id_tipo_descuento: int, id_modalidad_academica: int, id_alumno: int, db: Session):
    tipo_descuento = db.query(TipoDescuento).filter(
        TipoDescuento.id_tipo_descuento == id_tipo_descuento,
        TipoDescuento.estado == "activo"
    ).first()
    if not tipo_descuento:
        raise HTTPException(status_code=404, detail="Tipo de descuento no encontrado o inactivo")

    if tipo_descuento.uso_unico:
        usado = db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_alumno == id_alumno,
            DetalleProgramaAlumno.id_tipo_descuento == id_tipo_descuento,
            DetalleProgramaAlumno.estado.notin_(["postulante", "observado"])
        ).with_for_update().first()
        if usado:
            raise HTTPException(
                status_code=400,
                detail=f"El alumno ya utilizó el beneficio '{tipo_descuento.nombre}' anteriormente"
            )

    vinculo = db.query(ModalidadTipoDescuento).filter(
        ModalidadTipoDescuento.id_modalidad_academica == id_modalidad_academica,
        ModalidadTipoDescuento.id_tipo_descuento == id_tipo_descuento,
    ).first()
    if not vinculo:
        raise HTTPException(
            status_code=400,
            detail=f"El descuento '{tipo_descuento.nombre}' no está disponible para esta modalidad"
        )

    return tipo_descuento


def _cargar_con_relations(query):
    return query.options(
        joinedload(DetalleProgramaAlumno.alumno),
        joinedload(DetalleProgramaAlumno.modalidad_academica),
        joinedload(DetalleProgramaAlumno.programa_version_edicion),
        joinedload(DetalleProgramaAlumno.tipo_descuento),
        joinedload(DetalleProgramaAlumno.control_documentacion).joinedload(ControlDocumentacion.requisito),
    )


@router.post("/", response_model=DetalleProgramaAlumnoResponse, status_code=201)
def crear(data: DetalleProgramaAlumnoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.crear"))):
    modalidad = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.id_modalidad_academica == data.id_modalidad_academica
    ).first()
    if not modalidad:
        raise HTTPException(status_code=404, detail="Modalidad académica no encontrada")
    if modalidad.estado != "activo":
        raise HTTPException(status_code=400, detail="La modalidad académica no está activa")

    validar_modalidad_programa(data.id_modalidad_academica, data.id_programa_version_edicion, db)

    existente = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_alumno == data.id_alumno,
        DetalleProgramaAlumno.id_programa_version_edicion == data.id_programa_version_edicion,
    ).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail="El alumno ya está inscrito en esta edición del programa"
        )

    _validar_cupo(data.id_programa_version_edicion, db)

    descuento_aplicado = 0.0
    if data.id_tipo_descuento:
        td = _validar_descuento(data.id_tipo_descuento, data.id_modalidad_academica, data.id_alumno, db)
        descuento_aplicado = td.porcentaje

    nuevo = DetalleProgramaAlumno(**data.model_dump())
    nuevo.descuento_aplicado = descuento_aplicado
    nuevo.estado = "postulante"
    nuevo.fecha_inscripcion = date.today()
    db.add(nuevo)
    db.flush()

    generar_control_documentacion(nuevo.id_detalle_programa_alumno, data.id_modalidad_academica, db)

    if data.id_tipo_descuento:
        generar_control_descuento(nuevo.id_detalle_programa_alumno, data.id_modalidad_academica, data.id_tipo_descuento, db)

    db.commit()
    db.refresh(nuevo)
    return _cargar_con_relations(
        db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == nuevo.id_detalle_programa_alumno
        )
    ).first()


@router.get("/mis-inscripciones", response_model=list[DetalleProgramaAlumnoResponse])
def mis_inscripciones(db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")
    return _cargar_con_relations(
        db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_alumno == current_user.id_profile
        )
    ).all()


@router.get("/mi-inscripcion/{id}", response_model=DetalleProgramaAlumnoResponse)
def mi_inscripcion(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")
    detalle = _cargar_con_relations(
        db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == id,
            DetalleProgramaAlumno.id_alumno == current_user.id_profile,
        )
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    return detalle


@router.post("/auto-inscribir", response_model=DetalleProgramaAlumnoResponse, status_code=201)
def auto_inscribir(data: AutoInscribirRequest, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    existente = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_alumno == current_user.id_profile,
        DetalleProgramaAlumno.id_programa_version_edicion == data.id_programa_version_edicion,
    ).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail="Ya estás postulado a esta edición del programa"
        )

    modalidad = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.id_modalidad_academica == data.id_modalidad_academica
    ).first()
    if not modalidad:
        raise HTTPException(status_code=404, detail="Modalidad académica no encontrada")
    if modalidad.estado != "activo":
        raise HTTPException(status_code=400, detail="La modalidad académica no está activa")

    validar_modalidad_programa(data.id_modalidad_academica, data.id_programa_version_edicion, db)

    _validar_cupo(data.id_programa_version_edicion, db)

    descuento_aplicado = 0.0
    if data.id_tipo_descuento:
        td = _validar_descuento(data.id_tipo_descuento, data.id_modalidad_academica, current_user.id_profile, db)
        descuento_aplicado = td.porcentaje

    nuevo = DetalleProgramaAlumno(
        id_programa_version_edicion=data.id_programa_version_edicion,
        id_alumno=current_user.id_profile,
        id_modalidad_academica=data.id_modalidad_academica,
        id_tipo_descuento=data.id_tipo_descuento,
        descuento_aplicado=descuento_aplicado,
        estado="postulante",
        fecha_inscripcion=date.today(),
    )
    db.add(nuevo)
    db.flush()

    generar_control_documentacion(nuevo.id_detalle_programa_alumno, data.id_modalidad_academica, db)

    if data.id_tipo_descuento:
        generar_control_descuento(nuevo.id_detalle_programa_alumno, data.id_modalidad_academica, data.id_tipo_descuento, db)

    db.commit()
    db.refresh(nuevo)
    return _cargar_con_relations(
        db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == nuevo.id_detalle_programa_alumno
        )
    ).first()


@router.get("/", response_model=list[DetalleProgramaAlumnoResponse])
def listar(db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.ver"))):
    return _cargar_con_relations(db.query(DetalleProgramaAlumno)).all()


@router.get("/por-edicion/{id_edicion}", response_model=PaginatedInscripcionesResponse)
def inscripciones_por_edicion(
    id_edicion: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    estado: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.ver")),
):
    pve = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id_edicion
    ).first()
    if not pve:
        raise HTTPException(status_code=404, detail="Edición no encontrada")

    query = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_programa_version_edicion == id_edicion
    )

    if estado:
        query = query.filter(DetalleProgramaAlumno.estado == estado)

    if search:
        like = f"%{search}%"
        query = query.join(Alumno, DetalleProgramaAlumno.id_alumno == Alumno.id_alumno).filter(
            Alumno.nombre.ilike(like) | Alumno.apellido.ilike(like) | Alumno.ci.ilike(like)
        )

    total = query.count()
    pages = math.ceil(total / per_page) if total else 0
    offset = (page - 1) * per_page
    registros = query.order_by(DetalleProgramaAlumno.id_detalle_programa_alumno).offset(offset).limit(per_page).all()

    alumno_ids = {r.id_alumno for r in registros}
    modalidad_ids = {r.id_modalidad_academica for r in registros}
    td_ids = {r.id_tipo_descuento for r in registros if r.id_tipo_descuento}
    reg_ids = [r.id_detalle_programa_alumno for r in registros]

    alumnos_map = {
        a.id_alumno: a
        for a in db.query(Alumno).filter(Alumno.id_alumno.in_(alumno_ids)).all()
    } if alumno_ids else {}

    modalidades_map = {
        m.id_modalidad_academica: m
        for m in db.query(ModalidadAcademica).filter(
            ModalidadAcademica.id_modalidad_academica.in_(modalidad_ids)
        ).all()
    } if modalidad_ids else {}

    td_map = {
        t.id_tipo_descuento: t
        for t in db.query(TipoDescuento).filter(TipoDescuento.id_tipo_descuento.in_(td_ids)).all()
    } if td_ids else {}

    controles_all = db.query(ControlDocumentacion).filter(
        ControlDocumentacion.id_detalle_programa_alumno.in_(reg_ids)
    ).all() if reg_ids else []

    controles_por_detalle: dict[int, list[ControlDocumentacion]] = {}
    for c in controles_all:
        controles_por_detalle.setdefault(c.id_detalle_programa_alumno, []).append(c)

    items = []
    for reg in registros:
        alumno = alumnos_map.get(reg.id_alumno)
        modalidad = modalidades_map.get(reg.id_modalidad_academica)
        tipo_desc = td_map.get(reg.id_tipo_descuento) if reg.id_tipo_descuento else None
        controles = controles_por_detalle.get(reg.id_detalle_programa_alumno, [])
        docs_ok = sum(1 for c in controles if c.estado == "aceptado")

        items.append(InscripcionEdicionItem(
            id_detalle_programa_alumno=reg.id_detalle_programa_alumno,
            alumno=AlumnoBasico(
                id_alumno=alumno.id_alumno,
                nombre=alumno.nombre,
                apellido=alumno.apellido,
                ci=alumno.ci,
                correo=alumno.correo,
            ) if alumno else AlumnoBasico(id_alumno=0, nombre="N/A", apellido="", ci=None, correo=None),
            estado=reg.estado,
            modalidad=modalidad.nombre_modalidad if modalidad else "N/A",
            descuento_aplicado=float(reg.descuento_aplicado) if reg.descuento_aplicado else 0,
            tipo_descuento=tipo_desc.nombre if tipo_desc else None,
            modulo_inicio=reg.modulo_inicio,
            fecha_inscripcion=str(reg.fecha_inscripcion) if reg.fecha_inscripcion else None,
            docs_completados=docs_ok,
            docs_total=len(controles),
        ))

    return PaginatedInscripcionesResponse(
        items=items, total=total, page=page, per_page=per_page, pages=pages
    )


@router.get("/{id}", response_model=DetalleProgramaAlumnoResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.ver"))):
    detalle = _cargar_con_relations(
        db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == id
        )
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="No encontrado")
    return detalle


@router.patch("/{id}", response_model=DetalleProgramaAlumnoResponse)
def editar(id: int, data: DetalleProgramaAlumnoUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.editar"))):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="No encontrado")

    old_id_tipo_descuento = detalle.id_tipo_descuento
    new_id_tipo_descuento = data.id_tipo_descuento if "id_tipo_descuento" in data.model_fields_set else None
    descuento_cambio = new_id_tipo_descuento is not None and new_id_tipo_descuento != old_id_tipo_descuento

    update_data = data.model_dump(exclude_unset=True)
    update_data.pop("descuento_aplicado", None)

    if "modulo_inicio" in update_data and update_data["modulo_inicio"] is not None:
        if update_data["modulo_inicio"] < 1:
            raise HTTPException(status_code=400, detail="El módulo de inicio debe ser >= 1")

    if "estado" in update_data and update_data["estado"] is not None:
        _validar_transicion_estado(detalle.estado, update_data["estado"])

    for key, value in update_data.items():
        setattr(detalle, key, value)

    if descuento_cambio:
        if new_id_tipo_descuento:
            td = _validar_descuento(new_id_tipo_descuento, detalle.id_modalidad_academica, detalle.id_alumno, db)
            detalle.descuento_aplicado = float(td.porcentaje)
        else:
            detalle.descuento_aplicado = 0.0

    if descuento_cambio:
        if old_id_tipo_descuento:
            limpiar_control_descuento(detalle.id_detalle_programa_alumno, old_id_tipo_descuento, db)
        if new_id_tipo_descuento:
            generar_control_descuento(detalle.id_detalle_programa_alumno, detalle.id_modalidad_academica, new_id_tipo_descuento, db)

    db.commit()
    db.refresh(detalle)
    return _cargar_con_relations(
        db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == id
        )
    ).first()


@router.patch("/{id}/retirar", response_model=DetalleProgramaAlumnoResponse)
def retirar(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id,
        DetalleProgramaAlumno.id_alumno == current_user.id_profile,
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    _validar_transicion_estado(detalle.estado, "retirado")
    detalle.estado = "retirado"
    db.commit()
    return _cargar_con_relations(
        db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == id
        )
    ).first()


@router.delete("/{id}", response_model=DetalleProgramaAlumnoResponse)
def eliminar(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.editar"))):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="No encontrado")
    _validar_transicion_estado(detalle.estado, "retirado")
    detalle.estado = "retirado"
    db.commit()
    return _cargar_con_relations(
        db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == id
        )
    ).first()


@router.post("/{id}/transferir", response_model=DetalleProgramaAlumnoResponse, status_code=201)
def transferir(
    id: int,
    data: TransferirInscripcionRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.editar")),
):
    origen = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id
    ).first()
    if not origen:
        raise HTTPException(status_code=404, detail="Inscripción origen no encontrada")

    if origen.estado not in ("inscrito", "incorporado"):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede transferir una inscripción con estado '{origen.estado}'. "
                   f"Debe estar en 'inscrito' o 'incorporado'."
        )

    pve_destino = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == data.id_programa_version_edicion_destino
    ).first()
    if not pve_destino:
        raise HTTPException(status_code=404, detail="Edición destino no encontrada")

    if pve_destino.estado not in ("programado", "en_curso"):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede transferir a una edición con estado '{pve_destino.estado}'"
        )

    modalidad = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.id_modalidad_academica == data.id_modalidad_academica
    ).first()
    if not modalidad:
        raise HTTPException(status_code=404, detail="Modalidad académica no encontrada")

    pv_origen = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == origen.id_programa_version_edicion
    ).first()
    if pv_origen and pv_origen.id_programa_version != pve_destino.id_programa_version:
        raise HTTPException(
            status_code=400,
            detail="La edición destino debe pertenecer al mismo programa que la origen"
        )

    existente = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_alumno == origen.id_alumno,
        DetalleProgramaAlumno.id_programa_version_edicion == data.id_programa_version_edicion_destino,
    ).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail="El alumno ya tiene una inscripción en la edición destino"
        )

    _validar_cupo(data.id_programa_version_edicion_destino, db)

    _validar_transicion_estado(origen.estado, "incorporado")
    origen.estado = "incorporado"

    descuento_aplicado = 0.0
    if data.id_tipo_descuento:
        td = _validar_descuento(data.id_tipo_descuento, data.id_modalidad_academica, origen.id_alumno, db)
        descuento_aplicado = td.porcentaje

    if data.modulo_inicio < 1:
        raise HTTPException(
            status_code=400,
            detail="El módulo de inicio debe ser mayor o igual a 1"
        )

    destino = DetalleProgramaAlumno(
        id_programa_version_edicion=data.id_programa_version_edicion_destino,
        id_alumno=origen.id_alumno,
        id_modalidad_academica=data.id_modalidad_academica,
        id_tipo_descuento=data.id_tipo_descuento,
        descuento_aplicado=descuento_aplicado,
        modulo_inicio=data.modulo_inicio,
        estado="incorporado",
        fecha_inscripcion=date.today(),
    )
    db.add(destino)
    db.flush()

    historial = HistorialInscripcion(
        id_detalle_origen=origen.id_detalle_programa_alumno,
        id_detalle_destino=destino.id_detalle_programa_alumno,
        motivo=data.motivo,
    )
    db.add(historial)

    generar_control_documentacion(destino.id_detalle_programa_alumno, data.id_modalidad_academica, db)

    if data.id_tipo_descuento:
        generar_control_descuento(destino.id_detalle_programa_alumno, data.id_modalidad_academica, data.id_tipo_descuento, db)

    doc_carta = DocumentoIncorporacion(
        id_detalle_programa_alumno=destino.id_detalle_programa_alumno,
        tipo_documento="Carta de Solicitud de Incorporación",
        estado="pendiente",
    )
    db.add(doc_carta)

    db.commit()
    db.refresh(destino)
    return _cargar_con_relations(
        db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == destino.id_detalle_programa_alumno
        )
    ).first()


@router.get("/historial-transferencias/{id_alumno}")
def historial_transferencias(
    id_alumno: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.ver"))
):
    inscripciones = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_alumno == id_alumno,
    ).all()

    dpa_ids = [i.id_detalle_programa_alumno for i in inscripciones]
    transferencias = db.query(HistorialInscripcion).filter(
        (HistorialInscripcion.id_detalle_origen.in_(dpa_ids)) |
        (HistorialInscripcion.id_detalle_destino.in_(dpa_ids))
    ).all() if dpa_ids else []

    pve_ids = list({i.id_programa_version_edicion for i in inscripciones})
    pves = db.query(ProgramaVersionEdicion).options(
        joinedload(ProgramaVersionEdicion.programa_version)
            .joinedload(ProgramaVersion.programa)
    ).filter(
        ProgramaVersionEdicion.id_programa_version_edicion.in_(pve_ids)
    ).all() if pve_ids else []
    pve_map = {p.id_programa_version_edicion: p for p in pves}

    ins_map = {}
    for i in inscripciones:
        pve = pve_map.get(i.id_programa_version_edicion)
        pv = pve.programa_version if pve else None
        prog = pv.programa if pv else None
        ins_map[i.id_detalle_programa_alumno] = {
            "id_detalle_programa_alumno": i.id_detalle_programa_alumno,
            "id_programa_version_edicion": i.id_programa_version_edicion,
            "edicion_numero": pve.edicion if pve else 0,
            "anio": pve.anio if pve else 0,
            "semestre": pve.semestre if pve else 0,
            "programa_nombre": prog.nombre_programa if prog else "N/A",
            "estado": i.estado,
            "modulo_inicio": i.modulo_inicio,
        }

    historial_data = []
    for h in transferencias:
        historial_data.append({
            "id_historial": h.id_historial,
            "origen": ins_map.get(h.id_detalle_origen, {}),
            "destino": ins_map.get(h.id_detalle_destino, {}),
            "motivo": h.motivo,
            "fecha": str(h.created_at),
        })

    historial_data.sort(key=lambda x: x["fecha"])

    return {
        "id_alumno": id_alumno,
        "inscripciones": list(ins_map.values()),
        "transferencias": historial_data,
    }
