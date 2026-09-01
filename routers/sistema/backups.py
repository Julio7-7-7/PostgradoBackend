import io
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backups_service import (
    BACKUP_DIR, crear_archivo_backup, registrar, aplicar_retencion, restaurar_backup,
)
from database import get_db
from dependencies import get_current_user, require_permiso
from models.backup import Backup
from schemas.auth import UserResponse
from schemas.backup import BackupResponse, ImportarBackupResponse

router = APIRouter(
    prefix="/backups",
    tags=["Backups"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[BackupResponse])
def listar_backups(
    current_user: UserResponse = Depends(require_permiso("backups.ver")),
    db: Session = Depends(get_db),
):
    return db.query(Backup).order_by(Backup.created_at.desc()).all()


@router.post("/generar", response_model=BackupResponse)
def generar_backup(
    current_user: UserResponse = Depends(require_permiso("backups.crear")),
    db: Session = Depends(get_db),
):
    ruta, tamano = crear_archivo_backup()
    reg = registrar(db, ruta.name, str(ruta), tamano, "manual", "ok", None, current_user.id_usuario)
    aplicar_retencion(db)
    return reg


@router.get("/{id_backup}/descargar")
def descargar_backup(
    id_backup: int,
    current_user: UserResponse = Depends(require_permiso("backups.ver")),
    db: Session = Depends(get_db),
):
    reg = db.query(Backup).filter(Backup.id_backup == id_backup).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Backup no encontrado")
    ruta = Path(reg.ruta)
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Archivo de backup no existe en disco")
    return FileResponse(ruta, filename=reg.nombre)


@router.delete("/{id_backup}", response_model=dict)
def eliminar_backup(
    id_backup: int,
    current_user: UserResponse = Depends(require_permiso("backups.eliminar")),
    db: Session = Depends(get_db),
):
    reg = db.query(Backup).filter(Backup.id_backup == id_backup).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Backup no encontrado")
    try:
        p = Path(reg.ruta)
        if p.exists():
            p.unlink()
    except Exception:
        pass
    db.delete(reg)
    db.commit()
    return {"ok": True}


@router.post("/importar", response_model=ImportarBackupResponse)
async def importar_backup(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(require_permiso("backups.restaurar")),
    db: Session = Depends(get_db),
):
    contenido = await file.read()
    if not contenido:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    ok, mensaje, backup_previo_id = restaurar_backup(contenido, current_user.id_usuario)
    if not ok:
        raise HTTPException(status_code=400, detail=mensaje)
    return ImportarBackupResponse(
        ok=True,
        mensaje=mensaje,
        backup_previo_id=backup_previo_id,
    )
