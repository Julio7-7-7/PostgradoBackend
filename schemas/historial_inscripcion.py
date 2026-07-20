from datetime import datetime
from pydantic import BaseModel, ConfigDict


class HistorialInscripcionCreate(BaseModel):
    id_detalle_origen: int
    id_detalle_destino: int
    motivo: str


class HistorialInscripcionResponse(BaseModel):
    id_historial: int
    id_detalle_origen: int
    id_detalle_destino: int
    motivo: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HistorialInscripcionConDetalle(BaseModel):
    id_historial: int
    motivo: str
    created_at: datetime
    origen_edicion_numero: int | None
    origen_edicion_anio: int | None
    origen_programa_nombre: str | None
    destino_edicion_numero: int | None
    destino_edicion_anio: int | None
    destino_programa_nombre: str | None

    model_config = ConfigDict(from_attributes=True)
