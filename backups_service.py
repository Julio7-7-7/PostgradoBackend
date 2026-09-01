import gzip
import io
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException

from database import DATABASE_URL, SessionLocal
from models.backup import Backup

BASE_DIR = Path(__file__).resolve().parent
MEDIA_ROOT = BASE_DIR / "media"
BACKUP_DIR = BASE_DIR / "backups"
RETENCION_MAX = int(os.getenv("BACKUP_RETENCION", "30"))


def parse_db_url(url: str) -> dict:
    rest = url.split("://", 1)[1]
    userinfo, hostpart = rest.split("@", 1)
    user, _, password = userinfo.partition(":")
    if "/" in hostpart and ":" in hostpart.split("/", 1)[0]:
        host, port = hostpart.split("/", 1)[0].rsplit(":", 1)
        dbname = hostpart.split("/", 1)[1]
    elif "/" in hostpart:
        host = hostpart.split("/", 1)[0]
        port = "5432"
        dbname = hostpart.split("/", 1)[1]
    else:
        host = hostpart
        port = "5432"
        dbname = ""
    return {"user": user, "password": password, "host": host, "port": port, "dbname": dbname}


def dump_sql_bytes() -> bytes:
    cfg = parse_db_url(DATABASE_URL)
    env = {**os.environ, "PGPASSWORD": cfg["password"]}
    cmd = [
        "pg_dump",
        "-h", cfg["host"],
        "-p", cfg["port"],
        "-U", cfg["user"],
        "-d", cfg["dbname"],
        "--no-owner",
    ]
    result = subprocess.run(cmd, capture_output=True, env=env)
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar el volcado de la base de datos: {result.stderr.decode()[-500:]}",
        )
    return result.stdout


def crear_archivo_backup() -> tuple[Path, int]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = BACKUP_DIR / f"backup_{stamp}.bak"

    dump = dump_sql_bytes()
    with tarfile.open(ruta, "w:gz") as tar:
        info = tarfile.TarInfo("dump.sql")
        info.size = len(dump)
        tar.addfile(info, io.BytesIO(dump))
        if MEDIA_ROOT.exists():
            tar.add(str(MEDIA_ROOT), arcname="media")

    return ruta, ruta.stat().st_size


def registrar(db, nombre: str, ruta: str, tamano: int, origen: str, estado: str,
              observacion: str | None, user_id: int | None) -> Backup:
    reg = Backup(
        nombre=nombre,
        ruta=ruta,
        tamano_bytes=tamano,
        origen=origen,
        estado=estado,
        observacion=observacion,
        creado_por_id_usuario=user_id,
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)
    return reg


def aplicar_retencion(db):
    registros = db.query(Backup).order_by(Backup.created_at.desc()).all()
    for idx, reg in enumerate(registros):
        if idx >= RETENCION_MAX:
            try:
                p = Path(reg.ruta)
                if p.exists():
                    p.unlink()
            except Exception:
                pass
            db.delete(reg)
    db.commit()


def ejecutar_backup_automatico():
    """Genera un backup (origen 'auto') y aplica retención. Sin usuario (sistema)."""
    db = SessionLocal()
    try:
        ruta, tamano = crear_archivo_backup()
        registrar(
            db, ruta.name, str(ruta), tamano,
            "auto", "ok", "Backup automático programado", None,
        )
        aplicar_retencion(db)
    except Exception as e:
        db.rollback()
        print(f"[backups] Error en backup automático: {e}")
    finally:
        db.close()


def restaurar_backup(contenido: bytes, user_id: int | None) -> tuple[bool, str, int | None]:
    """Restaura un .bak. Devuelve (ok, mensaje, id_backup_previo)."""
    try:
        with tarfile.open(fileobj=io.BytesIO(contenido), mode="r:gz") as tar:
            with tempfile.TemporaryDirectory() as tmp:
                tar.extractall(tmp)
                dump_path = Path(tmp) / "dump.sql"
                if not dump_path.exists():
                    return False, "El backup no contiene dump.sql", None
                db = SessionLocal()
                try:
                    ruta_previo, tamano_previo = crear_archivo_backup()
                    reg_previo = registrar(
                        db, ruta_previo.name, str(ruta_previo), tamano_previo,
                        "previo_a_restaurar", "ok", "Backup automático antes de restaurar", user_id,
                    )
                finally:
                    db.close()

                cfg = parse_db_url(DATABASE_URL)
                env = {**os.environ, "PGPASSWORD": cfg["password"]}
                cmd = [
                    "psql",
                    "-h", cfg["host"],
                    "-p", cfg["port"],
                    "-U", cfg["user"],
                    "-d", cfg["dbname"],
                    "-f", str(dump_path),
                ]
                result = subprocess.run(cmd, capture_output=True, env=env)
                if result.returncode != 0:
                    return False, f"Error al restaurar: {result.stderr.decode()[-400:]}", None

                media_src = Path(tmp) / "media"
                if media_src.exists():
                    shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
                    shutil.copytree(media_src, MEDIA_ROOT)
                return True, "Backup restaurado correctamente", reg_previo.id_backup
    except Exception as e:
        return False, f"Error procesando el backup: {e}", None
