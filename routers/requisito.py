from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_permiso
from models.requisito import Requisito
from schemas.requisito import RequisitoCreate, RequisitoUpdate, RequisitoResponse
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/requisitos",
    tags=["Requisitos"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=RequisitoResponse, status_code=201)
def crear(data: RequisitoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("requisitos.crear"))):
    existente = db.query(Requisito).filter(
        Requisito.nombre == data.nombre,
        Requisito.id_modalidad_academica == data.id_modalidad_academica
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un requisito con ese nombre para esa modalidad académica")
    nuevo = Requisito(**data.model_dump())
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
            Requisito.id_modalidad_academica == requisito.id_modalidad_academica,
            Requisito.id_requisito != id
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail="Ya existe un requisito con ese nombre para esa modalidad académica")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(requisito, key, value)
    db.commit()
    db.refresh(requisito)
    return requisito

@router.delete("/{id}", status_code=204)
def eliminar(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("requisitos.editar"))):
    requisito = db.query(Requisito).filter(Requisito.id_requisito == id).first()
    if not requisito:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(requisito)
    db.commit()