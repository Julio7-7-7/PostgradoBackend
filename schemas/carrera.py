from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from enum import Enum

class EstadoCarreraEnum(str, Enum):
    activo = "activo"
    inactivo = "inactivo"

class CarreraBase(BaseModel):
    nombre: str
    sigla: str | None = None
    descripcion: str | None = None
    estado: EstadoCarreraEnum = EstadoCarreraEnum.activo

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres")
        if len(v.strip()) > 200:
            raise ValueError("El nombre no puede superar 200 caracteres")
        return v.strip().title()

class CarreraCreate(CarreraBase):
    pass

class CarreraUpdate(BaseModel):
    nombre: str | None = None
    sigla: str | None = None
    descripcion: str | None = None
    estado: EstadoCarreraEnum | None = None

class CarreraResponse(CarreraBase):
    id_carrera: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)