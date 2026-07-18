from fastapi import APIRouter, Depends, HTTPException
from datetime import date
from sqlalchemy.orm import Session, joinedload
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
from schemas.detalle_programa_alumno import DetalleProgramaAlumnoCreate, DetalleProgramaAlumnoUpdate, DetalleProgramaAlumnoResponse
from schemas.admin import AutoInscribirRequest
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/detalle-programa-alumno",
    tags=["Detalle Programa Alumno"],
    dependencies=[Depends(get_current_user)]
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

    for key, value in data.model_dump(exclude_unset=True).items():
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
    if detalle.estado in ("retirado", "finalizado", "graduado", "titulado"):
        raise HTTPException(status_code=400, detail=f"No se puede retirar de un estado '{detalle.estado}'")
    detalle.estado = "retirado"
    db.commit()
    return _cargar_con_relations(
        db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno == id
        )
    ).first()


@router.delete("/{id}", status_code=204)
def eliminar(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.editar"))):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(detalle)
    db.commit()
