from pydantic import BaseModel, field_validator, model_validator
from datetime import datetime, date
from enum import Enum
from schemas.programa_version import ProgramaVersionResponse
from schemas.modalidad import ModalidadResponse

class EstadoEdicionEnum(str, Enum):
    programado = "programado"
    en_curso = "en_curso"
    pausado = "pausado"
    finalizado = "finalizado"
    cancelado = "cancelado"

class ProgramaVersionEdicionBase(BaseModel):
    id_programa_version: int
    id_modalidad: int
    gestion: str | None = None
    es_historico: bool = False
    estado: EstadoEdicionEnum = EstadoEdicionEnum.programado
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    cupo_maximo: int | None = None
    descripcion: str | None = None
    precio: float | None = None

    @field_validator("cupo_maximo")
    @classmethod
    def validar_cupo_maximo(cls, v):
        if v is not None and v <= 0:
            raise ValueError("El cupo máximo debe ser mayor a 0")
        return v

    @field_validator("precio")
    @classmethod
    def validar_precio(cls, v):
        if v is not None and v < 0:
            raise ValueError("El precio no puede ser negativo")
        return v

    @model_validator(mode="after")
    def validar_fechas(self):
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin <= self.fecha_inicio:
                raise ValueError("La fecha de fin debe ser mayor a la fecha de inicio")
        return self

class ProgramaVersionEdicionCreate(ProgramaVersionEdicionBase):
    edicion: int | None = None

    @field_validator("edicion")
    @classmethod
    def validar_edicion(cls, v):
        if v is not None and v <= 0:
            raise ValueError("El número de edición debe ser mayor a 0")
        return v

class ProgramaVersionEdicionUpdate(BaseModel):
    id_modalidad: int | None = None
    gestion: str | None = None
    es_historico: bool | None = None
    estado: EstadoEdicionEnum | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    cupo_maximo: int | None = None
    descripcion: str | None = None
    precio: float | None = None

    @field_validator("cupo_maximo")
    @classmethod
    def validar_cupo_maximo(cls, v):
        if v is not None and v <= 0:
            raise ValueError("El cupo máximo debe ser mayor a 0")
        return v

    @field_validator("precio")
    @classmethod
    def validar_precio(cls, v):
        if v is not None and v < 0:
            raise ValueError("El precio no puede ser negativo")
        return v

class ProgramaVersionEdicionResponse(ProgramaVersionEdicionBase):
    id_programa_version_edicion: int
    edicion: int
    programa_version: ProgramaVersionResponse
    modalidad: ModalidadResponse
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
