from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from database import get_db
from models.programa import Programa
from models.programa_version import ProgramaVersion
from models.programa_version_edicion import ProgramaVersionEdicion
from schemas.programa_version import ProgramaVersionCreate, ProgramaVersionUpdate, ProgramaVersionResponse
import base64
import uuid
from pathlib import Path

router = APIRouter(
    prefix="/programas-version",
    tags=["Programas Version"]
)

FORMATOS_PERMITIDOS = {"jpeg", "jpg", "png", "gif", "webp"}
MEDIA_DIR = Path(__file__).parent.parent / "media" / "versiones"

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
        return f"/media/versiones/{filename}"
    except (ValueError, IndexError, base64.binascii.Error):
        raise HTTPException(status_code=400, detail="La foto no tiene un formato base64 válido")

def eliminar_foto(ruta: str | None):
    if ruta:
        archivo = Path(__file__).parent.parent / ruta.lstrip("/")
        if archivo.exists():
            archivo.unlink()

@router.post("/", response_model=ProgramaVersionResponse, status_code=201)
def crear(data: ProgramaVersionCreate, db: Session = Depends(get_db)):
    programa = db.query(Programa).filter(Programa.id_programa == data.id_programa).first()
    if not programa:
        raise HTTPException(status_code=404, detail="El programa especificado no existe")

    ultima = db.query(ProgramaVersion).filter(
        ProgramaVersion.id_programa == data.id_programa
    ).count()

    foto_ruta = guardar_foto_base64(data.foto) if data.foto else None

    try:
        nueva = ProgramaVersion(
            **data.model_dump(exclude={"foto"}),
            version=ultima + 1,
            foto=foto_ruta
        )
        db.add(nueva)
        db.commit()
        db.refresh(nueva)
        return nueva
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Conflicto: la versión ya fue creada por otra solicitud. Intente nuevamente."
        )

def _set_ediciones_activas(pv, db):
    pv.ediciones_count = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version == pv.id_programa_version,
        ProgramaVersionEdicion.es_historico == False
    ).count()

@router.get("/", response_model=list[ProgramaVersionResponse])
def listar(db: Session = Depends(get_db)):
    versiones = db.query(ProgramaVersion).options(joinedload(ProgramaVersion.programa)).all()
    for pv in versiones:
        _set_ediciones_activas(pv, db)
    return versiones

@router.get("/{id}", response_model=ProgramaVersionResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    pv = db.query(ProgramaVersion).options(joinedload(ProgramaVersion.programa)).filter(
        ProgramaVersion.id_programa_version == id
    ).first()
    if not pv:
        raise HTTPException(status_code=404, detail="No encontrado")
    _set_ediciones_activas(pv, db)
    return pv

@router.patch("/{id}", response_model=ProgramaVersionResponse)
def editar(id: int, data: ProgramaVersionUpdate, db: Session = Depends(get_db)):
    pv = db.query(ProgramaVersion).options(joinedload(ProgramaVersion.programa)).filter(
        ProgramaVersion.id_programa_version == id
    ).first()
    if not pv:
        raise HTTPException(status_code=404, detail="No encontrado")

    update_data = data.model_dump(exclude_unset=True)

    if "foto" in update_data:
        foto_value = update_data.pop("foto")
        if foto_value is not None:
            eliminar_foto(pv.foto)
            pv.foto = guardar_foto_base64(foto_value)
        else:
            eliminar_foto(pv.foto)
            pv.foto = None

    for key, value in update_data.items():
        setattr(pv, key, value)

    db.commit()
    db.refresh(pv)
    _set_ediciones_activas(pv, db)
    return pv
