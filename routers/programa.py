from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models.programa import Programa
from schemas.programa import ProgramaCreate, ProgramaUpdate, ProgramaResponse
import base64
import uuid
from pathlib import Path

router = APIRouter(
    prefix="/programas",
    tags=["Programas"]
)

MEDIA_DIR = Path(__file__).parent.parent / "media" / "programas"

FORMATOS_PERMITIDOS = {"jpeg", "jpg", "png", "gif", "webp"}

def guardar_foto_base64(data_url: str) -> str:
    try:
        header, encoded = data_url.split(",", 1)
        extension = header.split(";")[0].split("/")[1]
        if extension not in FORMATOS_PERMITIDOS:
            raise HTTPException(
                status_code=400,
                detail=f"Formato de imagen no soportado: {extension}. Use: {', '.join(FORMATOS_PERMITIDOS)}"
            )
        binary_data = base64.b64decode(encoded)
        filename = f"{uuid.uuid4()}.{extension}"
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        filepath = MEDIA_DIR / filename
        with open(filepath, "wb") as f:
            f.write(binary_data)
        return f"/media/programas/{filename}"
    except (ValueError, IndexError, base64.binascii.Error):
        raise HTTPException(status_code=400, detail="La foto no tiene un formato base64 válido")

def eliminar_foto(ruta: str | None):
    if ruta:
        archivo = Path(__file__).parent.parent / ruta.lstrip("/")
        if archivo.exists():
            archivo.unlink()

@router.post("/", response_model=ProgramaResponse, status_code=201)
def crear(data: ProgramaCreate, db: Session = Depends(get_db)):
    existente = db.query(Programa).filter(Programa.nombre_programa == data.nombre_programa).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un programa con ese nombre")

    foto_ruta = guardar_foto_base64(data.foto) if data.foto else None
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
            programa.foto = guardar_foto_base64(foto_value)
        else:
            eliminar_foto(programa.foto)
            programa.foto = None

    for key, value in update_data.items():
        setattr(programa, key, value)

    db.commit()
    programa = db.query(Programa).options(joinedload(Programa.tipo_programa)).filter(Programa.id_programa == id).first()
    return programa
