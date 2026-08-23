from pydantic import BaseModel, ConfigDict, model_validator
from datetime import datetime


class ControlDocContratacionCreate(BaseModel):
    id_requisito: int
    id_etapa: int


class ControlDocContratacionUpdate(BaseModel):
    estado: str | None = None
    notas: str | None = None


class ControlDocContratacionResponse(BaseModel):
    id_control_doc_contratacion: int
    id_contratacion: int
    id_requisito: int
    id_etapa: int
    url_documento: str | None = None
    estado: str
    notas: str | None = None
    requisito_nombre: str = ""
    etapa_nombre: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def fill_derived_fields(cls, data):
        requisito = getattr(data, 'requisito', None)
        if requisito:
            object.__setattr__(data, 'requisito_nombre', getattr(requisito, 'nombre', '') or '')
        etapa = getattr(data, 'etapa', None)
        if etapa:
            object.__setattr__(data, 'etapa_nombre', getattr(etapa, 'nombre', '') or '')
        return data
