from datetime import date, timedelta
from fastapi import HTTPException
from pathlib import Path
from sqlalchemy.orm import Session
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


def guardar_documento_base64(data_url: str, media_subdir: str = "documentos") -> str:
    headers = data_url.split(",", 1)[0]
    extension = headers.split(";")[0].split("/")[1]
    if extension not in FORMATOS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {extension}. Use: {', '.join(FORMATOS_PERMITIDOS)}",
        )
    return _decodificar_base64(data_url, extension, media_subdir)


def eliminar_foto(ruta: str | None):
    if ruta:
        archivo = Path(__file__).parent.parent / ruta.lstrip("/")
        if archivo.exists():
            archivo.unlink()


def es_dia_habil(fecha: date) -> bool:
    return fecha.weekday() < 5


def sumar_dias_habiles(fecha: date, dias: int) -> date:
    resultado = fecha
    agregados = 0
    while agregados < dias:
        resultado += timedelta(days=1)
        if es_dia_habil(resultado):
            agregados += 1
    return resultado


def esta_en_plazo_notas(fecha_fin: date, ventana: int = 5) -> bool:
    return date.today() <= sumar_dias_habiles(fecha_fin, ventana)


from models.detalle_programa_modulo import DetalleProgramaModulo


def resolver_modulo_inicio(id_pve: int, id_modulo_inicio: int | None, db: Session) -> tuple[int | None, int]:
    if id_modulo_inicio:
        dpm = db.query(DetalleProgramaModulo).filter(
            DetalleProgramaModulo.id_detalle_programa_modulo == id_modulo_inicio,
            DetalleProgramaModulo.id_programa_version_edicion == id_pve,
        ).first()
        if not dpm:
            raise HTTPException(
                status_code=400,
                detail="El módulo de inicio no pertenece a la edición especificada"
            )
        return (dpm.id_detalle_programa_modulo, dpm.orden)

    dpm = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == id_pve,
    ).order_by(DetalleProgramaModulo.orden).first()
    if dpm:
        return (dpm.id_detalle_programa_modulo, dpm.orden)
    return (None, 1)


def es_alumno_actual(usuario, id_alumno: int, db: Session) -> bool:
    from models.alumno import Alumno
    if usuario.profile_type == "alumno" and usuario.id_profile == id_alumno:
        return True
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id_alumno).first()
    if not alumno or not alumno.id_usuario:
        return False
    return alumno.id_usuario == usuario.id_usuario


def inferir_tipo_movimiento(dpa_origen, dpa_destino, db: Session) -> str:
    if dpa_origen.id_detalle_programa_alumno == dpa_destino.id_detalle_programa_alumno:
        return "reincorporacion"

    from models.programa_version import ProgramaVersion
    from models.programa_version_edicion import ProgramaVersionEdicion

    pv_origen = db.query(ProgramaVersion).join(
        ProgramaVersionEdicion,
        ProgramaVersionEdicion.id_programa_version == ProgramaVersion.id_programa_version,
    ).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == dpa_origen.id_programa_version_edicion
    ).first()

    pv_destino = db.query(ProgramaVersion).join(
        ProgramaVersionEdicion,
        ProgramaVersionEdicion.id_programa_version == ProgramaVersion.id_programa_version,
    ).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == dpa_destino.id_programa_version_edicion
    ).first()

    if pv_origen and pv_destino and pv_origen.id_programa_version == pv_destino.id_programa_version:
        return "migracion"

    raise ValueError(
        f"Tipo de movimiento no soportado: DPA origen {dpa_origen.id_detalle_programa_alumno} "
        f"(programa_version {pv_origen.id_programa_version if pv_origen else '?'}) → "
        f"DPA destino {dpa_destino.id_detalle_programa_alumno} "
        f"(programa_version {pv_destino.id_programa_version if pv_destino else '?'})"
    )
