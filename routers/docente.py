from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.docente import Docente
from schemas.docente import DocenteCreate, DocenteUpdate, DocenteResponse

router = APIRouter(
    prefix="/docentes",
    tags=["Docentes"]
)

@router.post("/", response_model=DocenteResponse, status_code=201)
def crear(data: DocenteCreate, db: Session = Depends(get_db)):
    existente = db.query(Docente).filter(
        (Docente.ci == data.ci) | (Docente.correo == data.correo)
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un docente con ese CI o correo")
    nuevo = Docente(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.get("/", response_model=list[DocenteResponse])
def listar(estado: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Docente)
    if estado:
        query = query.filter(Docente.estado == estado)
    return query.all()

@router.get("/{id}", response_model=DocenteResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    docente = db.query(Docente).filter(Docente.id_docente == id).first()
    if not docente:
        raise HTTPException(status_code=404, detail="No encontrado")
    return docente

@router.patch("/{id}", response_model=DocenteResponse)
def editar(id: int, data: DocenteUpdate, db: Session = Depends(get_db)):
    docente = db.query(Docente).filter(Docente.id_docente == id).first()
    if not docente:
        raise HTTPException(status_code=404, detail="No encontrado")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(docente, key, value)
    db.commit()
    db.refresh(docente)
    return docente

@router.patch("/{id}/cancelar", response_model=DocenteResponse)
def cancelar(id: int, db: Session = Depends(get_db)):
    docente = db.query(Docente).filter(Docente.id_docente == id).first()
    if not docente:
        raise HTTPException(status_code=404, detail="No encontrado")
    if docente.estado == "inactivo":
        raise HTTPException(status_code=400, detail="El docente ya está inactivo")
    docente.estado = "inactivo"
    db.commit()
    db.refresh(docente)
    return docente