from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, ConfigDict
from schemas.requisito import RequisitoResponse

class EstadoControlEnum(str, Enum):
    pendiente = "pendiente"
    entregado = "entregado"
    aceptado = "aceptado"
    rechazado = "rechazado"

class ControlDocumentacionBase(BaseModel):
    id_detalle_programa_alumno: int
    id_requisito: int
    url_documento: str | None = None
    obligatorio: bool = False
    estado: EstadoControlEnum = EstadoControlEnum.pendiente
    fecha_entrega: date | None = None
    fecha_revision: date | None = None
    observaciones: str | None = None

class ControlDocumentacionCreate(ControlDocumentacionBase):
    pass

class ControlDocumentacionUpdate(BaseModel):
    url_documento: str | None = None
    estado: EstadoControlEnum | None = None
    obligatorio: bool | None = None
    fecha_entrega: date | None = None
    fecha_revision: date | None = None
    observaciones: str | None = None

class ControlDocumentacionResponse(ControlDocumentacionBase):
    id_control_documentacion: int
    requisito: RequisitoResponse
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedControlDocumentacionResponse(BaseModel):
    items: list[ControlDocumentacionResponse]
    total: int
    page: int
    per_page: int
    pages: int