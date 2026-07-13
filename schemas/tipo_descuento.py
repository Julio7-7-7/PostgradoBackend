from pydantic import BaseModel, field_validator, ConfigDict
from datetime import datetime
from enum import Enum
from typing import Optional
from schemas.modalidad_academica import ModalidadAcademicaResponse
from schemas.requisito import RequisitoResponse

class EstadoTipoDescuentoEnum(str, Enum):
    activo = "activo"
    inactivo = "inactivo"

class TipoDescuentoBase(BaseModel):
    nombre: str
    porcentaje: float
    descripcion: str | None = None
    estado: EstadoTipoDescuentoEnum = EstadoTipoDescuentoEnum.activo

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres")
        return v.strip().title()

    @field_validator("porcentaje")
    @classmethod
    def validar_porcentaje(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("El porcentaje debe estar entre 0 y 100")
        return v

class TipoDescuentoCreate(TipoDescuentoBase):
    modalidades: list[int] = []
    requisitos: list[int] = []

class TipoDescuentoUpdate(BaseModel):
    nombre: str | None = None
    porcentaje: float | None = None
    descripcion: str | None = None
    estado: EstadoTipoDescuentoEnum | None = None
    modalidades: list[int] | None = None
    requisitos: list[int] | None = None

class TipoDescuentoResponse(TipoDescuentoBase):
    id_tipo_descuento: int
    modalidades: list[ModalidadAcademicaResponse] = []
    requisitos: list[RequisitoResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
