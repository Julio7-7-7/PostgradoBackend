from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from enum import Enum

class EstadoEnum(str, Enum):
    activo = "activo"
    inactivo = "inactivo"

class TipoProgramaBase(BaseModel):
    nombre: str
    estado: EstadoEnum = EstadoEnum.activo
    cupo_minimo: int | None = None
    duracion_minima_meses: int | None = None

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres")
        if len(v.strip()) > 100:
            raise ValueError("El nombre no puede superar 100 caracteres")
        return v.strip().title()

    @field_validator("cupo_minimo")
    @classmethod
    def validar_cupo_minimo(cls, v):
        if v is not None and v <= 0:
            raise ValueError("El cupo mínimo debe ser mayor a 0")
        return v

    @field_validator("duracion_minima_meses")
    @classmethod
    def validar_duracion(cls, v):
        if v is not None and v <= 0:
            raise ValueError("La duración mínima debe ser mayor a 0")
        return v

class TipoProgramaCreate(TipoProgramaBase):
    pass

class TipoProgramaUpdate(BaseModel):
    nombre: str | None = None
    estado: EstadoEnum | None = None
    cupo_minimo: int | None = None
    duracion_minima_meses: int | None = None

class TipoProgramaResponse(TipoProgramaBase):
    id_tipo_programa: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)