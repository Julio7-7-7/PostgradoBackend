from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_permiso
from models.requisito import Requisito
from schemas.requisito import RequisitoCreate, RequisitoUpdate, RequisitoResponse
from schemas.auth import UserResponse
from .utils import guardar_foto_base64, eliminar_foto

router = APIRouter(
    prefix="/requisitos",
    tags=["Requisitos"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=RequisitoResponse, status_code=201)
def crear(data: RequisitoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("requisitos.crear"))):
    existente = db.query(Requisito).filter(Requisito.nombre == data.nombre).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un requisito con ese nombre")

    imagen_ruta = guardar_foto_base64(data.imagen_url, "requisitos") if data.imagen_url else None

    nuevo = Requisito(
        nombre=data.nombre,
        descripcion=data.descripcion,
        imagen_url=imagen_ruta,
        estado=data.estado,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.get("/", response_model=list[RequisitoResponse])
def listar(db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("requisitos.ver"))):
    return db.query(Requisito).all()

@router.get("/{id}", response_model=RequisitoResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("requisitos.ver"))):
    requisito = db.query(Requisito).filter(Requisito.id_requisito == id).first()
    if not requisito:
        raise HTTPException(status_code=404, detail="No encontrado")
    return requisito

@router.patch("/{id}", response_model=RequisitoResponse)
def editar(id: int, data: RequisitoUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("requisitos.editar"))):
    requisito = db.query(Requisito).filter(Requisito.id_requisito == id).first()
    if not requisito:
        raise HTTPException(status_code=404, detail="No encontrado")
    if data.nombre:
        existente = db.query(Requisito).filter(
            Requisito.nombre == data.nombre,
            Requisito.id_requisito != id
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail="Ya existe un requisito con ese nombre")

    update_data = data.model_dump(exclude_unset=True)

    if "imagen_url" in update_data:
        if update_data["imagen_url"]:
            eliminar_foto(requisito.imagen_url)
            update_data["imagen_url"] = guardar_foto_base64(update_data["imagen_url"], "requisitos")
        else:
            eliminar_foto(requisito.imagen_url)
            update_data["imagen_url"] = None

    for key, value in update_data.items():
        setattr(requisito, key, value)
    db.commit()
    db.refresh(requisito)
    return requisito
