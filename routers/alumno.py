from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_permiso
from models.alumno import Alumno
from schemas.alumno import AlumnoCreate, AlumnoUpdate, AlumnoResponse
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/alumnos",
    tags=["Alumnos"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=AlumnoResponse, status_code=201)
def crear(data: AlumnoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.crear"))):
    if data.ci:
        if db.query(Alumno).filter(Alumno.ci == data.ci).first():
            raise HTTPException(status_code=400, detail="Ya existe un alumno con ese CI")
    if data.pasaporte:
        if db.query(Alumno).filter(Alumno.pasaporte == data.pasaporte).first():
            raise HTTPException(status_code=400, detail="Ya existe un alumno con ese pasaporte")
    if db.query(Alumno).filter(Alumno.correo == data.correo).first():
        raise HTTPException(status_code=400, detail="Ya existe un alumno con ese correo")
    nuevo = Alumno(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.get("/", response_model=list[AlumnoResponse])
def listar(db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.ver"))):
    return db.query(Alumno).all()

@router.get("/{id}", response_model=AlumnoResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.ver"))):
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="No encontrado")
    return alumno

@router.patch("/{id}", response_model=AlumnoResponse)
def editar(id: int, data: AlumnoUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.editar"))):
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="No encontrado")
    if data.ci:
        if db.query(Alumno).filter(Alumno.ci == data.ci, Alumno.id_alumno != id).first():
            raise HTTPException(status_code=400, detail="Ya existe un alumno con ese CI")
    if data.pasaporte:
        if db.query(Alumno).filter(Alumno.pasaporte == data.pasaporte, Alumno.id_alumno != id).first():
            raise HTTPException(status_code=400, detail="Ya existe un alumno con ese pasaporte")
    if data.correo:
        if db.query(Alumno).filter(Alumno.correo == data.correo, Alumno.id_alumno != id).first():
            raise HTTPException(status_code=400, detail="Ya existe un alumno con ese correo")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(alumno, key, value)
    db.commit()
    db.refresh(alumno)
    return alumno

@router.delete("/{id}", status_code=204)
def eliminar(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.editar"))):
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(alumno)
    db.commit()