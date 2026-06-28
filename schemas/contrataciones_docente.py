from pydantic import BaseModel, ConfigDict
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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
