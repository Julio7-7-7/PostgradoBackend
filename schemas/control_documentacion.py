from pydantic import BaseModel, ConfigDict
from datetime import datetime, date

class ControlDocumentacionBase(BaseModel):
    id_detalle_programa_alumno: int
    id_requisito: int
    entregado: bool = False
    fecha_entrega: date | None = None
    observaciones: str | None = None

class ControlDocumentacionCreate(ControlDocumentacionBase):
    pass

class ControlDocumentacionResponse(ControlDocumentacionBase):
    id_control_documentacion: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)