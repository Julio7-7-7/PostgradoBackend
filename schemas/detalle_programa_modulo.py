from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from datetime import datetime, date
from enum import Enum
from schemas.modulo import ModuloResponse
from schemas.docente import DocenteResponse
from schemas.contrataciones_docente import ContratacionDocenteResponse
from schemas.enums import ModalidadEnum

class EstadoDetalleEnum(str, Enum):
    programado = "programado"
    en_curso = "en_curso"
    reprogramado = "reprogramado"
    finalizado = "finalizado"

class DetalleProgramaModuloBase(BaseModel):
    id_programa_version_edicion: int
    id_modulo: int
    modalidad: ModalidadEnum | None = None
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
    modalidad: ModalidadEnum | None = None
    orden: int | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    estado: EstadoDetalleEnum | None = None
    motivo: str | None = None

    @model_validator(mode="after")
    def validar_fechas(self):
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin <= self.fecha_inicio:
                raise ValueError("La fecha fin debe ser mayor a la fecha inicio")
        return self

class ReordenarItem(BaseModel):
    id_detalle: int
    orden: int

class ReordenarRequest(BaseModel):
    id_edicion: int
    ordenes: list[ReordenarItem]

class DetalleProgramaModuloResponse(DetalleProgramaModuloBase):
    id_detalle_programa_modulo: int
    id_programa_version: int
    id_programa: int
    edicion: int
    programa_nombre: str
    programa_version_numero: int
    fecha_inicio_edicion: date | None = None
    fecha_fin_edicion: date | None = None
    modulo: ModuloResponse
    docente: DocenteResponse | None = None
    modalidad: ModalidadEnum | None = None
    contratacion: ContratacionDocenteResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)