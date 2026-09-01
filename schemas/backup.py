from datetime import datetime
from pydantic import BaseModel


class BackupResponse(BaseModel):
    id_backup: int
    nombre: str
    tamano_bytes: int
    origen: str
    estado: str
    observacion: str | None = None
    creado_por_id_usuario: int | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class ImportarBackupResponse(BaseModel):
    ok: bool
    mensaje: str
    backup_previo_id: int | None = None
