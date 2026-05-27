from pydantic import BaseModel, field_validator, model_validator
from datetime import datetime, date
from enum import Enum
from schemas.modulo import ModuloResponse
from schemas.docente import DocenteResponse
from schemas.modalidad import ModalidadResponse

class EstadoDetalleEnum(str, Enum):
    programado = "programado"
    en_curso = "en_curso"
    pausado = "pausado"
    reprogramado = "reprogramado"
    finalizado = "finalizado"
    cancelado = "cancelado"

class DetalleProgramaModuloBase(BaseModel):
    id_programa_version_edicion: int
    id_modulo: int
    id_docente: int | None = None
    id_modalidad: int | None = None
    orden: int
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    estado: EstadoDetalleEnum = EstadoDetalleEnum.programado

    @field_validator("orden")
    @classmethod
    def validar_orden(cls, v):
        if v <= 0:
            raise ValueError("El orden debe ser mayor a 0")
        return v

    @model_validator(mode="after")
    def validar_fechas(self):
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin <= self.fecha_inicio:
                raise ValueError("La fecha fin debe ser mayor a la fecha inicio")
        return self

class DetalleProgramaModuloCreate(DetalleProgramaModuloBase):
    pass

class DetalleProgramaModuloUpdate(BaseModel):
    id_docente: int | None = None
    id_modalidad: int | None = None
    orden: int | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    estado: EstadoDetalleEnum | None = None
    motivo: str | None = None

class DetalleProgramaModuloResponse(DetalleProgramaModuloBase):
    id_detalle_programa_modulo: int
    modulo: ModuloResponse
    docente: DocenteResponse | None = None
    modalidad: ModalidadResponse | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True