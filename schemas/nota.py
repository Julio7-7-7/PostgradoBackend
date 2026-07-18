from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class NotaCreate(BaseModel):
    id_detalle_programa_alumno: int
    id_detalle_programa_modulo: int
    nota: Decimal
    tipo: str = "final"
    fecha: date
    observaciones: str | None = None


class NotaUpdate(BaseModel):
    nota: Decimal | None = None
    tipo: str | None = None
    fecha: date | None = None
    observaciones: str | None = None


class NotaResponse(BaseModel):
    id_nota: int
    id_detalle_programa_alumno: int
    id_detalle_programa_modulo: int
    nota: Decimal
    tipo: str
    fecha: date
    observaciones: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
