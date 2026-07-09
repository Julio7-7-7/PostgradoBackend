from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_permiso
from models.modalidad_academica import ModalidadAcademica
from schemas.modalidad_academica import ModalidadAcademicaCreate, ModalidadAcademicaUpdate, ModalidadAcademicaResponse
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/modalidades-academicas",
    tags=["Modalidades Academicas"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=ModalidadAcademicaResponse, status_code=201)
def crear(data: ModalidadAcademicaCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("modalidades_academicas.crear"))):
    existente = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.nombre_modalidad == data.nombre_modalidad
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una modalidad académica con ese nombre")
    nueva = ModalidadAcademica(**data.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

@router.get("/", response_model=list[ModalidadAcademicaResponse])
def listar(db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("modalidades_academicas.ver"))):
    return db.query(ModalidadAcademica).all()

@router.get("/{id}", response_model=ModalidadAcademicaResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("modalidades_academicas.ver"))):
    modalidad = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.id_modalidad_academica == id
    ).first()
    if not modalidad:
        raise HTTPException(status_code=404, detail="No encontrado")
    return modalidad

@router.patch("/{id}", response_model=ModalidadAcademicaResponse)
def editar(id: int, data: ModalidadAcademicaUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("modalidades_academicas.editar"))):
    modalidad = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.id_modalidad_academica == id
    ).first()
    if not modalidad:
        raise HTTPException(status_code=404, detail="No encontrado")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(modalidad, key, value)
    db.commit()
    db.refresh(modalidad)
    return modalidad

@router.delete("/{id}", status_code=204)
def eliminar(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("modalidades_academicas.editar"))):
    modalidad = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.id_modalidad_academica == id
    ).first()
    if not modalidad:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(modalidad)
    db.commit()