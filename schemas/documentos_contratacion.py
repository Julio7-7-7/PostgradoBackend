from pydantic import BaseModel, ConfigDict
from datetime import datetime
from enum import Enum


class TipoDocumentoContratoEnum(str, Enum):
    invitacion = "invitacion"
    aceptacion = "aceptacion"
    solicitud = "solicitud"
    contrato = "contrato"


class DocumentoContratacionBase(BaseModel):
    id_contratacion: int
    tipo: TipoDocumentoContratoEnum


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
