from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from enum import Enum

class EstadoRequisitoEnum(str, Enum):
    activo = "activo"
    inactivo = "inactivo"

class RequisitoBase(BaseModel):
    nombre: str
    descripcion: str | None = None
    imagen_url: str | None = None
    estado: EstadoRequisitoEnum = EstadoRequisitoEnum.activo

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres")
        if len(v.strip()) > 200:
            raise ValueError("El nombre no puede superar 200 caracteres")
        return v.strip().title()

class RequisitoCreate(RequisitoBase):
    pass

class RequisitoUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    imagen_url: str | None = None
    estado: EstadoRequisitoEnum | None = None

class RequisitoResponse(RequisitoBase):
    id_requisito: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
