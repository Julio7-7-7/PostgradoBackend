from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from enum import Enum

class EstadoAlumnoEnum(str, Enum):
    postulante = "postulante"
    inscrito = "inscrito"
    en_curso = "en_curso"
    finalizado = "finalizado"
    retirado = "retirado"

class DetalleProgramaAlumnoBase(BaseModel):
    id_programa_version_edicion: int
    id_alumno: int
    id_modalidad_academica: int
    descuento: float = 0.0
    estado: EstadoAlumnoEnum = EstadoAlumnoEnum.postulante
    fecha_inscripcion: date | None = None

class DetalleProgramaAlumnoCreate(DetalleProgramaAlumnoBase):
    pass

class DetalleProgramaAlumnoResponse(DetalleProgramaAlumnoBase):
    id_detalle_programa_alumno: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)