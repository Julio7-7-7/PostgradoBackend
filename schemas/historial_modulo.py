from pydantic import BaseModel, ConfigDict
from datetime import datetime, date

class HistorialModuloBase(BaseModel):
    id_detalle_programa_modulo: int
    estado_anterior: str | None = None
    estado_nuevo: str | None = None
    motivo: str
    fecha_inicio_original: date | None = None
    fecha_fin_original: date | None = None
    fecha_inicio_nuevo: date | None = None
    fecha_fin_nuevo: date | None = None

class HistorialModuloResponse(HistorialModuloBase):
    id_historial: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DetalleContexto(BaseModel):
    programa_nombre: str
    programa_version: int
    edicion: int
    modulo_sigla: str
    modulo_nombre: str
    orden: int

class HistorialModuloResponseEnriquecido(HistorialModuloResponse):
    detalle: DetalleContexto | None = None
