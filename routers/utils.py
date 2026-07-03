from fastapi import HTTPException
from pathlib import Path
import base64
import math
import uuid

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB global

MAGIC_BYTES: dict[str, bytes] = {
    "jpeg": b"\xff\xd8\xff",
    "jpg": b"\xff\xd8\xff",
    "png": b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a",
    "gif": b"\x47\x49\x46\x38",
    "webp": b"\x52\x49\x46\x46",
    "pdf": b"\x25\x50\x44\x46",
}

FORMATOS_IMAGEN = {"jpeg", "jpg", "png", "gif", "webp"}
FORMATOS_PDF = {"pdf"}
FORMATOS_PERMITIDOS = FORMATOS_IMAGEN | FORMATOS_PDF


def _estimar_tamano(base64_str: str, max_bytes: int = MAX_FILE_SIZE) -> None:
    """Estima el tamaño real desde el string base64 sin decodificar.
    Base64 produce ~4/3 del tamaño original, rechaza si excede."""
    decoded_estimate = math.ceil(len(base64_str) * 3 / 4)
    if decoded_estimate > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Archivo demasiado grande (~{_formato_bytes(decoded_estimate)}). "
                   f"Máximo permitido: {_formato_bytes(max_bytes)}.",
        )


def _formato_bytes(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024*1024):.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


def _magic_bytes_valido(data: bytes, extension: str) -> None:
    expected = MAGIC_BYTES.get(extension)
    if not expected:
        return
    if len(data) < len(expected) or not data.startswith(expected):
        raise HTTPException(
            status_code=400,
            detail=f"El contenido del archivo no coincide con el formato esperado (.{extension}). "
                   f"Archivo corrupto o camuflado.",
        )


def _decodificar_base64(data_url: str, extension: str, media_subdir: str) -> str:
    try:
        header, encoded = data_url.split(",", 1)
        mime_type = header.split(";")[0].split("/")[1]
        if mime_type != extension:
            raise HTTPException(
                status_code=400,
                detail=f"El tipo MIME '{mime_type}' no coincide con la extensión esperada '{extension}'.",
            )
        _estimar_tamano(encoded)
        binary_data = base64.b64decode(encoded)
        _magic_bytes_valido(binary_data, extension)
        filename = f"{uuid.uuid4()}.{extension}"
        MEDIA_DIR = Path(__file__).parent.parent / "media" / media_subdir
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        filepath = MEDIA_DIR / filename
        with open(filepath, "wb") as f:
            f.write(binary_data)
        return f"/media/{media_subdir}/{filename}"
    except (ValueError, IndexError, base64.binascii.Error):
        raise HTTPException(status_code=400, detail="El archivo no tiene un formato base64 válido")


def guardar_foto_base64(data_url: str, media_subdir: str = "programas") -> str:
    headers = data_url.split(",", 1)[0]
    extension = headers.split(";")[0].split("/")[1]
    if extension not in FORMATOS_IMAGEN:
        raise HTTPException(
            status_code=400,
            detail=f"Formato de imagen no soportado: {extension}. Use: {', '.join(FORMATOS_IMAGEN)}"
        )
    return _decodificar_base64(data_url, extension, media_subdir)


def guardar_pdf_base64(data_url: str, media_subdir: str = "contratos") -> str:
    headers = data_url.split(",", 1)[0]
    extension = headers.split(";")[0].split("/")[1]
    if extension not in FORMATOS_PDF:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {extension}. Solo se acepta PDF.",
        )
    return _decodificar_base64(data_url, extension, media_subdir)


def eliminar_foto(ruta: str | None):
    if ruta:
        archivo = Path(__file__).parent.parent / ruta.lstrip("/")
        if archivo.exists():
            archivo.unlink()
