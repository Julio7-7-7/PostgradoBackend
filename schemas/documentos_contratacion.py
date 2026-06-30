from pydantic import BaseModel, ConfigDict
from datetime import datetime
from enum import Enum


class DocumentoContratacionBase(BaseModel):
    id_contratacion: int
    tipo: str


class DocumentoContratacionCreate(DocumentoContratacionBase):
    archivo_pdf_base64: str | None = None


class DocumentoContratacionUpdate(BaseModel):
    archivo_pdf_base64: str | None = None


class DocumentoContratacionResponse(DocumentoContratacionBase):
    id_documento: int
    archivo_pdf: str | None = None
    fecha_subida: datetime
    orden: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
