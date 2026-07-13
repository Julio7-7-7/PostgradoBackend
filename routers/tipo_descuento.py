from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from dependencies import get_current_user, require_permiso
from models.tipo_descuento import TipoDescuento
from models.modalidad_academica import ModalidadAcademica
from models.requisito import Requisito
from schemas.tipo_descuento import TipoDescuentoCreate, TipoDescuentoUpdate, TipoDescuentoResponse
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/tipos-descuento",
    tags=["Tipos de Descuento"],
    dependencies=[Depends(get_current_user)]
)

def _cargar_con_relations(query):
    return query.options(
        joinedload(TipoDescuento.modalidades),
        joinedload(TipoDescuento.requisitos),
    )

def _sincronizar(tipo: TipoDescuento, modalidades_ids: list[int], requisitos_ids: list[int], db: Session):
    if modalidades_ids is not None:
        modalidades = db.query(ModalidadAcademica).filter(
            ModalidadAcademica.id_modalidad_academica.in_(modalidades_ids)
        ).all()
        tipo.modalidades = modalidades

    if requisitos_ids is not None:
        requisitos = db.query(Requisito).filter(
            Requisito.id_requisito.in_(requisitos_ids)
        ).all()
        tipo.requisitos = requisitos

    db.commit()
    db.refresh(tipo)


@router.post("/", response_model=TipoDescuentoResponse, status_code=201)
def crear(data: TipoDescuentoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_descuento.crear"))):
    existente = db.query(TipoDescuento).filter(TipoDescuento.nombre == data.nombre).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un tipo de descuento con ese nombre")

    modalidades_ids = data.modalidades
    requisitos_ids = data.requisitos

    nuevo = TipoDescuento(
        nombre=data.nombre,
        porcentaje=data.porcentaje,
        descripcion=data.descripcion,
        estado=data.estado,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    _sincronizar(nuevo, modalidades_ids, requisitos_ids, db)

    return _cargar_con_relations(
        db.query(TipoDescuento).filter(TipoDescuento.id_tipo_descuento == nuevo.id_tipo_descuento)
    ).first()


@router.get("/", response_model=list[TipoDescuentoResponse])
def listar(db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_descuento.ver"))):
    return _cargar_con_relations(
        db.query(TipoDescuento)
    ).all()


@router.get("/{id}", response_model=TipoDescuentoResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_descuento.ver"))):
    tipo = _cargar_con_relations(
        db.query(TipoDescuento).filter(TipoDescuento.id_tipo_descuento == id)
    ).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="No encontrado")
    return tipo


@router.patch("/{id}", response_model=TipoDescuentoResponse)
def editar(id: int, data: TipoDescuentoUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_descuento.editar"))):
    tipo = db.query(TipoDescuento).filter(TipoDescuento.id_tipo_descuento == id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="No encontrado")

    if data.nombre is not None:
        existente = db.query(TipoDescuento).filter(
            TipoDescuento.nombre == data.nombre,
            TipoDescuento.id_tipo_descuento != id
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail="Ya existe un tipo de descuento con ese nombre")

    for key, value in data.model_dump(exclude_unset=True, exclude={"modalidades", "requisitos"}).items():
        setattr(tipo, key, value)
    db.commit()

    _sincronizar(tipo, data.modalidades, data.requisitos, db)

    return _cargar_con_relations(
        db.query(TipoDescuento).filter(TipoDescuento.id_tipo_descuento == id)
    ).first()


@router.delete("/{id}", status_code=204)
def eliminar(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_descuento.editar"))):
    tipo = db.query(TipoDescuento).filter(TipoDescuento.id_tipo_descuento == id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(tipo)
    db.commit()
