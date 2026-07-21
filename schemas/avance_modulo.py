from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class AvanceModuloCreate(BaseModel):
    id_detalle_programa_alumno: int
    id_detalle_programa_modulo: int
    completado_en_edicion: int
    fecha_completion: date | None = None


class AvanceModuloResponse(BaseModel):
    id_avance: int
    id_detalle_programa_alumno: int
    id_detalle_programa_modulo: int
    completado_en_edicion: int
    fecha_completion: date | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModuloTranscriptItem(BaseModel):
    id_detalle_programa_modulo: int
    modulo_nombre: str
    modulo_orden: int
    nota: float | None
    nota_tipo: str | None
    completado_en_edicion: int | None
    edicion_numero: int | None
    edicion_anio: int | None
    edicion_semestre: int | None
    fecha_completion: date | None


class InscripcionTranscriptItem(BaseModel):
    id_detalle_programa_alumno: int
    estado: str
    edicion_id: int
    edicion_numero: int | None
    edicion_anio: int | None
    edicion_semestre: int | None
    programa_nombre: str
    modalidad_nombre: str
    modulo_inicio: int
    modulos: list[ModuloTranscriptItem]
    promedio: float | None


class TranscriptResponse(BaseModel):
    id_alumno: int
    alumno_nombre: str
    alumno_apellido: str
    alumno_ci: str | None
    inscripciones: list[InscripcionTranscriptItem]
    promedio_general: float | None
