from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, computed_field
from schemas.enums import NotaCalificacion, clasificar_nota


class NotaCreate(BaseModel):
    id_detalle_programa_alumno: int
    id_detalle_programa_modulo: int
    nota: Decimal = Field(ge=0, le=100)
    fecha: date


class NotaUpdate(BaseModel):
    nota: Decimal | None = Field(default=None, ge=0, le=100)
    fecha: date | None = None


class NotaResponse(BaseModel):
    id_nota: int
    id_detalle_programa_alumno: int
    id_detalle_programa_modulo: int
    nota: Decimal
    fecha: date
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def calificacion(self) -> NotaCalificacion:
        return clasificar_nota(float(self.nota))


class NotaItem(BaseModel):
    id_nota: int
    id_detalle_programa_modulo: int
    modulo_nombre: str
    modulo_orden: int
    nota: float
    calificacion: NotaCalificacion
    fecha: date
    created_at: datetime
    updated_at: datetime


class AlumnoInfo(BaseModel):
    id_alumno: int | None
    nombre: str
    apellido: str
    ci: str | None


class NotaEdicionResponse(BaseModel):
    id_detalle_programa_alumno: int
    alumno: AlumnoInfo | None
    modulo_inicio: int
    estado: str
    notas: list[NotaItem]
    promedio: int


class DocenteEdicionInfo(BaseModel):
    id_programa_version_edicion: int
    edicion_numero: int
    anio: int
    semestre: int
    programa_nombre: str
    estado: str


class DocenteModuloInfo(BaseModel):
    id_detalle_programa_modulo: int
    nombre: str
    sigla: str
    orden: int
    estado: str
    fecha_inicio: date | None
    fecha_fin: date | None
    num_alumnos: int


class DocenteAlumnoInfo(BaseModel):
    id_detalle_programa_alumno: int
    alumno: AlumnoInfo | None
    modulo_inicio: int
    estado: str
    notas_count: int


class NotaDocenteResponse(BaseModel):
    edicion: DocenteEdicionInfo
    modulos: list[DocenteModuloInfo]
    alumnos: list[DocenteAlumnoInfo]


class ModuloInfo(BaseModel):
    id_detalle_programa_modulo: int
    nombre: str
    sigla: str
    orden: int
    estado: str
    fecha_inicio: date | None
    fecha_fin: date | None


class ModuloEdicionInfo(BaseModel):
    id_programa_version_edicion: int
    edicion_numero: int
    anio: int
    semestre: int
    programa_nombre: str


class ModuloNotaItem(BaseModel):
    id_nota: int
    nota: float
    calificacion: NotaCalificacion
    fecha: date
    created_at: datetime
    updated_at: datetime


class ModuloAlumnoInfo(BaseModel):
    id_detalle_programa_alumno: int
    alumno: AlumnoInfo | None
    modulo_inicio: int
    estado: str
    notas: list[ModuloNotaItem]
    promedio: int


class NotaModuloResponse(BaseModel):
    modulo: ModuloInfo
    edicion: ModuloEdicionInfo
    alumnos: list[ModuloAlumnoInfo]


class ModuloTranscriptItem(BaseModel):
    id_detalle_programa_modulo: int
    modulo_nombre: str
    modulo_orden: int
    nota: float | None
    calificacion: str | None
    edicion_numero: int | None
    edicion_anio: int | None
    edicion_semestre: int | None


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


class EdicionInfoItem(BaseModel):
    id_programa_version_edicion: int
    edicion_numero: int | None
    anio: int | None
    semestre: int | None
    programa_nombre: str
    estado: str | None


class TranscriptResponse(BaseModel):
    id_alumno: int
    alumno_nombre: str
    alumno_apellido: str
    alumno_ci: str | None
    inscripciones: list[InscripcionTranscriptItem]
    ediciones_info: list[EdicionInfoItem]
    promedio_general: float | None
