from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_permiso
from models.tipo_programa import TipoPrograma
from schemas.tipo_programa import TipoProgramaCreate, TipoProgramaUpdate, TipoProgramaResponse
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/tipos-programa",
    tags=["Tipos de Programa"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=TipoProgramaResponse, status_code=201)
def crear(data: TipoProgramaCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_programa.crear"))):
    existente = db.query(TipoPrograma).filter(TipoPrograma.nombre == data.nombre).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un tipo de programa con ese nombre")
    nuevo = TipoPrograma(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.get("/", response_model=list[TipoProgramaResponse])
def listar(db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_programa.ver"))):
    return db.query(TipoPrograma).all()

@router.get("/{id}", response_model=TipoProgramaResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_programa.ver"))):
    tipo = db.query(TipoPrograma).filter(TipoPrograma.id_tipo_programa == id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="No encontrado")
    return tipo

@router.patch("/{id}", response_model=TipoProgramaResponse)
def editar(id: int, data: TipoProgramaUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_programa.editar"))):
    tipo = db.query(TipoPrograma).filter(TipoPrograma.id_tipo_programa == id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="No encontrado")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(tipo, key, value)
    db.commit()
    db.refresh(tipo)
    return tipo
