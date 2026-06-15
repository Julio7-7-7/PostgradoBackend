
from datetime import datetime, date
from enum import Enum
from schemas.alumno import AlumnoResponse
from schemas.modalidad_academica import ModalidadAcademicaResponse

class EstadoDetalleAlumnoEnum(str, Enum):
    postulante = "postulante"
    inscrito = "inscrito"
    en_curso = "en_curso"
    finalizado = "finalizado"
    graduado = "graduado"
    titulado = "titulado"
    retirado = "retirado"
    convalidando = "convalidando"

class DetalleProgramaAlumnoBase(BaseModel):
    id_programa_version_edicion: int
    id_alumno: int
    id_modalidad_academica: int
    id_tipo_descuento: int | None = None
    descuento_aplicado: float = 0.0
    estado: EstadoDetalleAlumnoEnum = EstadoDetalleAlumnoEnum.postulante
    fecha_inscripcion: date | None = None

    @field_validator("descuento_aplicado")
    @classmethod
    def validar_descuento(cls, v):
        if v < 0 or v > 100:
            raise ValueError("El descuento debe estar entre 0 y 100")
        return v

class DetalleProgramaAlumnoCreate(DetalleProgramaAlumnoBase):
    pass

class DetalleProgramaAlumnoUpdate(BaseModel):
    id_tipo_descuento: int | None = None
    descuento_aplicado: float | None = None
    estado: EstadoDetalleAlumnoEnum | None = None
    fecha_inscripcion: date | None = None

class DetalleProgramaAlumnoResponse(DetalleProgramaAlumnoBase):
    id_detalle_programa_alumno: int
    alumno: AlumnoResponse
    modalidad_academica: ModalidadAcademicaResponse
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)