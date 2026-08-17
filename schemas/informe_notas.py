from datetime import date, datetime
from pydantic import BaseModel


class InformeNotasCreate(BaseModel):
    id_programa_version_edicion: int
    numero_tanda: int
    alumnos_ids: list[int]
    observaciones: str | None = None


class InformeNotasResponse(BaseModel):
    id_informe: int
    id_programa_version_edicion: int
    numero_tanda: int
    fecha_emision: date
    alumnos_ids: list[int]
    estado: str
    observaciones: str | None
    created_at: datetime
    updated_at: datetime


class InformeNotasElegible(BaseModel):
    id_alumno: int
    id_detalle_programa_alumno: int
    nombre: str
    apellido: str
    ci: str | None


class InformeNotasAlumnoDetalle(BaseModel):
    id_alumno: int
    nombre: str
    apellido: str
    ci: str | None
    notas_aprobadas: bool
    pagos_completos: bool
