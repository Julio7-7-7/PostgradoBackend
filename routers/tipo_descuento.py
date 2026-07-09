from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_permiso
from models.tipo_descuento import TipoDescuento
from schemas.tipo_descuento import TipoDescuentoCreate, TipoDescuentoUpdate, TipoDescuentoResponse
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/tipos-descuento",
    tags=["Tipos de Descuento"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=TipoDescuentoResponse, status_code=201)
def crear(data: TipoDescuentoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_descuento.crear"))):
    existente = db.query(TipoDescuento).filter(TipoDescuento.nombre == data.nombre).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un tipo de descuento con ese nombre")
    nuevo = TipoDescuento(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.get("/", response_model=list[TipoDescuentoResponse])
def listar(db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_descuento.ver"))):
    return db.query(TipoDescuento).all()

@router.get("/{id}", response_model=TipoDescuentoResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_descuento.ver"))):
    tipo = db.query(TipoDescuento).filter(TipoDescuento.id_tipo_descuento == id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="No encontrado")
    return tipo

@router.patch("/{id}", response_model=TipoDescuentoResponse)
def editar(id: int, data: TipoDescuentoUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_descuento.editar"))):
    tipo = db.query(TipoDescuento).filter(TipoDescuento.id_tipo_descuento == id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="No encontrado")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(tipo, key, value)
    db.commit()
    db.refresh(tipo)
    return tipo

@router.delete("/{id}", status_code=204)
def eliminar(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_descuento.editar"))):
    tipo = db.query(TipoDescuento).filter(TipoDescuento.id_tipo_descuento == id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(tipo)
    db.commit()