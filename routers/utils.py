from fastapi import HTTPException
from pathlib import Path
import base64
import uuid

FORMATOS_PERMITIDOS = {"jpeg", "jpg", "png", "gif", "webp"}

def guardar_foto_base64(data_url: str, media_subdir: str = "programas") -> str:
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
        MEDIA_DIR = Path(__file__).parent.parent / "media" / media_subdir
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        filepath = MEDIA_DIR / filename
        with open(filepath, "wb") as f:
            f.write(binary_data)
        return f"/media/{media_subdir}/{filename}"
    except (ValueError, IndexError, base64.binascii.Error):
        raise HTTPException(status_code=400, detail="La foto no tiene un formato base64 válido")

def eliminar_foto(ruta: str | None):
    if ruta:
        archivo = Path(__file__).parent.parent / ruta.lstrip("/")
        if archivo.exists():
            archivo.unlink()
