from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from datetime import datetime, date
from enum import Enum
from schemas.programa_version import ProgramaVersionResponse
from schemas.enums import ModalidadEnum

class EstadoEdicionEnum(str, Enum):
    programado = "programado"
    en_curso = "en_curso"
    reprogramado = "reprogramado"
    finalizado = "finalizado"

class SemestreAnioValidator(BaseModel):
    semestre: int | None = None
    anio: int | None = None

    @field_validator("semestre")
    @classmethod
    def validar_semestre(cls, v):
        if v is not None and v not in (1, 2):
            raise ValueError("El semestre debe ser 1 o 2")
        return v

    @field_validator("anio")
    @classmethod
    def validar_anio(cls, v):
        if v is not None and (v < 2000 or v > 2100):
            raise ValueError("El año debe estar entre 2000 y 2100")
        return v

class ProgramaVersionEdicionBase(BaseModel):
    id_programa_version: int
    modalidad: ModalidadEnum
    semestre: int | None = None
    anio: int | None = None
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

    @field_validator("semestre")
    @classmethod
    def validar_semestre(cls, v):
        if v is not None and v not in (1, 2):
            raise ValueError("El semestre debe ser 1 o 2")
        return v

    @field_validator("anio")
    @classmethod
    def validar_anio(cls, v):
        if v is not None and (v < 2000 or v > 2100):
            raise ValueError("El año debe estar entre 2000 y 2100")
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
    modalidad: ModalidadEnum | None = None
    semestre: int | None = None
    anio: int | None = None
    es_historico: bool | None = None
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

    @field_validator("semestre")
    @classmethod
    def validar_semestre(cls, v):
        if v is not None and v not in (1, 2):
            raise ValueError("El semestre debe ser 1 o 2")
        return v

    @field_validator("anio")
    @classmethod
    def validar_anio(cls, v):
        if v is not None and (v < 2000 or v > 2100):
            raise ValueError("El año debe estar entre 2000 y 2100")
        return v

class ProgramaVersionEdicionResponse(ProgramaVersionEdicionBase):
    id_programa_version_edicion: int
    edicion: int
    gestion: str
    programa_version: ProgramaVersionResponse
    modalidad: ModalidadEnum
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
