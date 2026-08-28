from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel


class InformeNotasRequest(BaseModel):
    id_programa_version_edicion: int
    tipo: Literal["parcial", "final"] = "parcial"
    id_modulos: list[int] = []
    id_carrera: int | None = None


class InformeAlumnoNota(BaseModel):
    id_alumno: int
    id_detalle_programa_alumno: int
    nombre: str
    apellido: str
    ci: str | None
    nota: float | None
    aprobada: bool


class InformeModulo(BaseModel):
    id_detalle_programa_modulo: int
    nombre_modulo: str
    sigla: str
    fecha_inicio: date | None
    fecha_fin: date | None
    docente: str | None
    alumnos: list[InformeAlumnoNota]


class InformeMatrizColumna(BaseModel):
    id_detalle_programa_modulo: int
    nombre_modulo: str
    sigla: str


class InformeMatrizFila(BaseModel):
    id_alumno: int
    id_detalle_programa_alumno: int
    nombre: str
    apellido: str
    ci: str | None
    notas: list[float | None]
    aprobada: bool
    elegible: bool
    motivo_exclusion: str | None


class InformeCarrera(BaseModel):
    id_carrera: int | None
    nombre: str
    modulos: list[InformeModulo] = []
    matriz_columnas: list[InformeMatrizColumna] = []
    matriz_filas: list[InformeMatrizFila] = []


class InformeResumen(BaseModel):
    total_alumnos: int
    total_aprobados: int
    total_reprobados: int
    elegibles: int
    carreras: list[dict]


class InformePreviewResponse(BaseModel):
    tipo: str
    id_programa_version_edicion: int
    edicion_desc: str
    programa_nombre: str
    version: int
    numero_tanda: int
    timestamp: datetime
    carreras: list[InformeCarrera]
    todas_notas: bool
    edicion_finalizada: bool
    resumen: InformeResumen


class InformeNotasResponse(BaseModel):
    id_informe: int
    id_programa_version_edicion: int
    numero_tanda: int
    tipo: str
    fecha_emision: date
    generado_at: datetime | None
    estado: str
    observaciones: str | None
    contenido: dict | None
    certificados_count: int = 0
    created_at: datetime
    updated_at: datetime