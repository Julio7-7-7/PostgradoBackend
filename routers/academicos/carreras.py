from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from dependencies import get_current_user, require_permiso
from models.carrera import Carrera
from schemas.carrera import CarreraCreate, CarreraUpdate, CarreraResponse
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/carreras",
    tags=["Carreras"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/", response_model=CarreraResponse, status_code=201)
def crear(data: CarreraCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("carreras.crear"))):
    existente = db.query(Carrera).filter(
        func.lower(func.trim(Carrera.nombre)) == data.nombre.strip().lower()
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una carrera con ese nombre")

    nueva = Carrera(
        nombre=data.nombre,
        sigla=data.sigla,
        descripcion=data.descripcion,
        estado=data.estado,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.get("/", response_model=list[CarreraResponse])
def listar(solo_activas: bool = False, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("carreras.ver"))):
    query = db.query(Carrera)
    if solo_activas:
        query = query.filter(Carrera.estado == "activo")
    return query.order_by(Carrera.nombre).all()


@router.get("/{id}", response_model=CarreraResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("carreras.ver"))):
    carrera = db.query(Carrera).filter(Carrera.id_carrera == id).first()
    if not carrera:
        raise HTTPException(status_code=404, detail="No encontrado")
    return carrera


@router.patch("/{id}", response_model=CarreraResponse)
def editar(id: int, data: CarreraUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("carreras.editar"))):
    carrera = db.query(Carrera).filter(Carrera.id_carrera == id).first()
    if not carrera:
        raise HTTPException(status_code=404, detail="No encontrado")

    if data.nombre and data.nombre != carrera.nombre:
        existente = db.query(Carrera).filter(
            func.lower(func.trim(Carrera.nombre)) == data.nombre.strip().lower()
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail="Ya existe una carrera con ese nombre")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(carrera, key, value)

    db.commit()
    db.refresh(carrera)
    return carrera


@router.patch("/{id}/cambiar-estado", response_model=CarreraResponse)
def cambiar_estado(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("carreras.editar"))):
    carrera = db.query(Carrera).filter(Carrera.id_carrera == id).first()
    if not carrera:
        raise HTTPException(status_code=404, detail="No encontrado")
    carrera.estado = "inactivo" if carrera.estado == "activo" else "activo"
    db.commit()
    db.refresh(carrera)
    return carrera