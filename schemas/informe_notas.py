from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel


class InformeNotasRequest(BaseModel):
    """Solicitud de generación de informe de notas (formato horizontal por carrera).

    - tipo 'borrador': columnas = módulos seleccionados (pueden ser menos que la edición),
      no emite certificados, marca de agua BORRADOR. Pueden generarse varias tandas.
    - tipo 'final': columnas = todos los módulos de la edición, único por edición,
      emite certificados a los alumnos completos. Sin marca de agua.
    """

    id_programa_version_edicion: int
    tipo: Literal["borrador", "final"] = "borrador"
    id_modulos: list[int] = []
    id_carrera: int | None = None


class CertificadoEmitirRequest(BaseModel):
    id_programa_version_edicion: int
    alumnos_ids: list[int]


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
    promedio: float | None
    aprobada: bool
    elegible: bool
    estado: str


class InformeCarrera(BaseModel):
    id_carrera: int | None
    nombre: str
    matriz_columnas: list[InformeMatrizColumna] = []
    matriz_filas: list[InformeMatrizFila] = []


class InformeResumen(BaseModel):
    total_alumnos: int
    total_aprobados: int
    total_reprobados: int
    completos: int
    carreras: list[dict]


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
    emitido_por: int | None = None
    emitido_por_nombre: str | None = None
    created_at: datetime
    updated_at: datetime