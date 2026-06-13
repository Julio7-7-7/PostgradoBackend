from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from enum import Enum
from schemas.programa_version import ProgramaVersionResponse

class EstadoModuloEnum(str, Enum):
    activo = "activo"
    inactivo = "inactivo"

class ModuloBase(BaseModel):
    id_programa_version: int
    sigla: str
    nombre_modulo: str
    horas_academicas: int
    creditos: int
    descripcion: str | None = None
    estado: EstadoModuloEnum = EstadoModuloEnum.activo

    @field_validator("sigla")
    @classmethod
    def validar_sigla(cls, v):
        if len(v.strip()) > 20:
            raise ValueError("La sigla no puede superar 20 caracteres")
        return v.strip().upper()

    @field_validator("nombre_modulo")
    @classmethod
    def validar_nombre(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres")
        if len(v.strip()) > 200:
            raise ValueError("El nombre no puede superar 200 caracteres")
        return v.strip().title()

    @field_validator("horas_academicas", "creditos")
    @classmethod
    def validar_positivos(cls, v):
        if v <= 0:
            raise ValueError("El valor debe ser mayor a 0")
        return v

class ModuloCreate(ModuloBase):
    pass

class ModuloUpdate(BaseModel):
    id_programa_version: int | None = None
    sigla: str | None = None
    nombre_modulo: str | None = None
    horas_academicas: int | None = None
    creditos: int | None = None
    descripcion: str | None = None
    estado: EstadoModuloEnum | None = None

    @field_validator("sigla")
    @classmethod
    def validar_sigla(cls, v):
        if v is None:
            return v
        if len(v.strip()) > 20:
            raise ValueError("La sigla no puede superar 20 caracteres")
        return v.strip().upper()

    @field_validator("nombre_modulo")
    @classmethod
    def validar_nombre(cls, v):
        if v is None:
            return v
        if len(v.strip()) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres")
        if len(v.strip()) > 200:
            raise ValueError("El nombre no puede superar 200 caracteres")
        return v.strip().title()

    @field_validator("horas_academicas", "creditos")
    @classmethod
    def validar_positivos(cls, v):
        if v is None:
            return v
        if v <= 0:
            raise ValueError("El valor debe ser mayor a 0")
        return v

class ModuloResponse(ModuloBase):
    id_modulo: int
    programa_version: ProgramaVersionResponse
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
