from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from enum import Enum

class EstadoModalidadAcademicaEnum(str, Enum):
    activo = "activo"
    inactivo = "inactivo"

class ModalidadAcademicaBase(BaseModel):
    nombre_modalidad: str
    descripcion: str | None = None
    requiere_titulo: bool = False
    estado: EstadoModalidadAcademicaEnum = EstadoModalidadAcademicaEnum.activo

    @field_validator("nombre_modalidad")
    @classmethod
    def validar_nombre(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres")
        if len(v.strip()) > 100:
            raise ValueError("El nombre no puede superar 100 caracteres")
        return v.strip().title()

class ModalidadAcademicaCreate(ModalidadAcademicaBase):
    pass

class ModalidadAcademicaUpdate(BaseModel):
    nombre_modalidad: str | None = None
    descripcion: str | None = None
    requiere_titulo: bool | None = None
    estado: EstadoModalidadAcademicaEnum | None = None

class ModalidadAcademicaResponse(ModalidadAcademicaBase):
    id_modalidad_academica: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)