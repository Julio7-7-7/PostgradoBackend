from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from dependencies import get_current_user, require_permiso
from models.etapa_contratacion import EtapaContratacion
from models.etapa_requisito import EtapaRequisito
from models.requisito import Requisito
from schemas.etapa_contratacion import (
    EtapaContratacionCreate,
    EtapaContratacionUpdate,
    EtapaContratacionResponse,
    EtapaRequisitoAsignar,
)
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/etapas-contratacion",
    tags=["Etapas de Contratacion"],
    dependencies=[Depends(get_current_user)],
)


def _cargar_con_requisitos(query):
    return query.options(
        joinedload(EtapaContratacion.etapa_requisitos).joinedload(EtapaRequisito.requisito),
    )


def _sincronizar_requisitos(etapa: EtapaContratacion, requisitos_data: list[EtapaRequisitoAsignar], db: Session):
    db.query(EtapaRequisito).filter(EtapaRequisito.id_etapa == etapa.id_etapa).delete()
    for req_data in requisitos_data:
        requisito = db.query(Requisito).filter(Requisito.id_requisito == req_data.id_requisito).first()
        if not requisito:
            raise HTTPException(status_code=400, detail=f"El requisito {req_data.id_requisito} no existe")
        db.add(EtapaRequisito(
            id_etapa=etapa.id_etapa,
            id_requisito=req_data.id_requisito,
            orden=req_data.orden,
        ))
    db.commit()


@router.post("/", response_model=EtapaContratacionResponse, status_code=201)
def crear(data: EtapaContratacionCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.crear"))):
    existente = db.query(EtapaContratacion).filter(
        EtapaContratacion.id_tipo_programa == data.id_tipo_programa,
        EtapaContratacion.nombre == data.nombre,
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una etapa con ese nombre para este tipo de programa")

    if data.orden is not None:
        orden = data.orden
    else:
        max_orden = db.query(EtapaContratacion.orden).filter(
            EtapaContratacion.id_tipo_programa == data.id_tipo_programa
        ).order_by(EtapaContratacion.orden.desc()).first()
        orden = (max_orden[0] + 1) if max_orden else 1

    nueva = EtapaContratacion(
        id_tipo_programa=data.id_tipo_programa,
        nombre=data.nombre,
        orden=orden,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)

    if data.requisitos:
        _sincronizar_requisitos(nueva, data.requisitos, db)

    return _cargar_con_requisitos(db.query(EtapaContratacion)).filter(
        EtapaContratacion.id_etapa == nueva.id_etapa
    ).first()


@router.get("/", response_model=list[EtapaContratacionResponse])
def listar(tipo_programa_id: int | None = None, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.ver"))):
    query = db.query(EtapaContratacion)
    if tipo_programa_id:
        query = query.filter(EtapaContratacion.id_tipo_programa == tipo_programa_id)
    return _cargar_con_requisitos(query.order_by(EtapaContratacion.orden.asc())).all()


@router.get("/{id}", response_model=EtapaContratacionResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.ver"))):
    etapa = _cargar_con_requisitos(db.query(EtapaContratacion)).filter(EtapaContratacion.id_etapa == id).first()
    if not etapa:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    return etapa


@router.patch("/{id}", response_model=EtapaContratacionResponse)
def editar(id: int, data: EtapaContratacionUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.editar"))):
    etapa = db.query(EtapaContratacion).filter(EtapaContratacion.id_etapa == id).first()
    if not etapa:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(etapa, key, value)
    db.commit()
    db.refresh(etapa)
    return _cargar_con_requisitos(db.query(EtapaContratacion)).filter(EtapaContratacion.id_etapa == id).first()


@router.patch("/{id}/requisitos", response_model=EtapaContratacionResponse)
def actualizar_requisitos(id: int, requisitos: list[EtapaRequisitoAsignar], db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.editar"))):
    etapa = db.query(EtapaContratacion).filter(EtapaContratacion.id_etapa == id).first()
    if not etapa:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")

    _sincronizar_requisitos(etapa, requisitos, db)
    return _cargar_con_requisitos(db.query(EtapaContratacion)).filter(EtapaContratacion.id_etapa == id).first()


@router.delete("/{id}", status_code=204)
def eliminar(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.editar"))):
    etapa = db.query(EtapaContratacion).filter(EtapaContratacion.id_etapa == id).first()
    if not etapa:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")

    from models.contratacion_docente import ContratacionDocente
    contratacion_con_etapa = db.query(ContratacionDocente).filter(ContratacionDocente.id_etapa_actual == id).first()
    if contratacion_con_etapa:
        raise HTTPException(status_code=400, detail="No se puede eliminar una etapa que está en uso por una contratación")

    db.query(EtapaRequisito).filter(EtapaRequisito.id_etapa == id).delete()
    db.delete(etapa)
    db.commit()
