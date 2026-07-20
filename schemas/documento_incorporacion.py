from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class DocumentoIncorporacionCreate(BaseModel):
    id_detalle_programa_alumno: int
    tipo_documento: str


class DocumentoIncorporacionUpdate(BaseModel):
    estado: str | None = None
    url_documento: str | None = None
    observaciones: str | None = None
    fecha_entrega: date | None = None
    fecha_revision: date | None = None


class DocumentoIncorporacionResponse(BaseModel):
    id_documento_incorporacion: int
    id_detalle_programa_alumno: int
    tipo_documento: str
    estado: str
    url_documento: str | None
    observaciones: str | None
    fecha_entrega: date | None
    fecha_revision: date | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
