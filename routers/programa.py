from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models.programa import Programa
from schemas.programa import ProgramaCreate, ProgramaUpdate, ProgramaResponse
from .utils import guardar_foto_base64, eliminar_foto

router = APIRouter(
    prefix="/programas",
    tags=["Programas"]
)

@router.post("/", response_model=ProgramaResponse, status_code=201)
def crear(data: ProgramaCreate, db: Session = Depends(get_db)):
    existente = db.query(Programa).filter(Programa.nombre_programa == data.nombre_programa).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un programa con ese nombre")

    foto_ruta = guardar_foto_base64(data.foto, "programas") if data.foto else None
    nuevo = Programa(**data.model_dump(exclude={"foto"}), foto=foto_ruta)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.get("/", response_model=list[ProgramaResponse])
def listar(db: Session = Depends(get_db)):
    return db.query(Programa).options(joinedload(Programa.tipo_programa)).all()

@router.get("/{id}", response_model=ProgramaResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    programa = db.query(Programa).options(joinedload(Programa.tipo_programa)).filter(Programa.id_programa == id).first()
    if not programa:
        raise HTTPException(status_code=404, detail="No encontrado")
    return programa

@router.patch("/{id}", response_model=ProgramaResponse)
def editar(id: int, data: ProgramaUpdate, db: Session = Depends(get_db)):
    programa = db.query(Programa).options(joinedload(Programa.tipo_programa)).filter(Programa.id_programa == id).first()
    if not programa:
        raise HTTPException(status_code=404, detail="No encontrado")

    update_data = data.model_dump(exclude_unset=True)

    if "foto" in update_data:
        foto_value = update_data.pop("foto")
        if foto_value is not None:
            eliminar_foto(programa.foto)
            programa.foto = guardar_foto_base64(foto_value, "programas")
        else:
            eliminar_foto(programa.foto)
            programa.foto = None

    for key, value in update_data.items():
        setattr(programa, key, value)

    db.commit()
    programa = db.query(Programa).options(joinedload(Programa.tipo_programa)).filter(Programa.id_programa == id).first()
    return programa
