from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime, date

class HistorialModuloBase(BaseModel):
    id_detalle_programa_modulo: int
    estado_anterior: str
    estado_nuevo: str
    motivo: str
    fecha_inicio_original: date | None = None
    fecha_fin_original: date | None = None

    @field_validator("motivo")
    @classmethod
    def validar_motivo(cls, v):
        if len(v.strip()) < 10:
            raise ValueError("El motivo debe tener al menos 10 caracteres")
        return v.strip()

class HistorialModuloCreate(HistorialModuloBase):
    pass

class HistorialModuloResponse(HistorialModuloBase):
    id_historial: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)