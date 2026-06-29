from pydantic import BaseModel, ConfigDict, model_validator
from datetime import datetime, date
from enum import Enum
from schemas.docente import DocenteResponse


class ContratacionEstadoEnum(str, Enum):
    pendiente = "pendiente"
    en_curso = "en_curso"
    formalizado = "formalizado"
    truncado = "truncado"


class ContratacionDocenteBase(BaseModel):
    id_docente: int
    id_detalle_modulo: int
    monto: float | None = None


class ContratacionDocenteCreate(ContratacionDocenteBase):
    pass


class ContratacionDocenteUpdate(BaseModel):
    monto: float | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    estado: ContratacionEstadoEnum | None = None


class ContratacionDocenteResponse(ContratacionDocenteBase):
    id_contratacion: int
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    estado: ContratacionEstadoEnum
    docente: DocenteResponse
    id_programa: int
    programa_nombre: str
    modulo_sigla: str
    modulo_nombre: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def fill_dates_from_detalle(cls, data):
        if hasattr(data, 'detalle_modulo') and data.detalle_modulo is not None:
            if data.fecha_inicio is None and data.detalle_modulo.fecha_inicio:
                data.fecha_inicio = data.detalle_modulo.fecha_inicio
            if data.fecha_fin is None and data.detalle_modulo.fecha_fin:
                data.fecha_fin = data.detalle_modulo.fecha_fin
        return data
