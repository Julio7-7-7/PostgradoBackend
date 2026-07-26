from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class SolicitudIncorporacionCreate(BaseModel):
    id_programa_version_edicion: int | None = None
    id_modalidad_academica: int | None = None
    id_tipo_descuento: int | None = None
    modulo_inicio: int = 1
    url_documento: str = ""
    id_requisito: int | None = None


class AprobarSolicitudRequest(BaseModel):
    id_programa_version_edicion: int | None = None
    id_modalidad_academica: int | None = None
    id_tipo_descuento: int | None = None
    modulo_inicio: int = 1


class SolicitudDocumentoResponse(BaseModel):
    id_solicitud_documento: int
    id_requisito: int
    nombre_requisito: str = ""
    url_documento: str
    estado: str
    fecha_entrega: datetime

    model_config = ConfigDict(from_attributes=True)


class SolicitudIncorporacionResponse(BaseModel):
    id_solicitud: int
    id_detalle_programa_alumno: int
    id_programa_version_edicion: int
    estado: str
    observaciones: str | None
    fecha_revision: date | None
    created_at: datetime
    updated_at: datetime
    documentos: list[SolicitudDocumentoResponse]

    model_config = ConfigDict(from_attributes=True)


class SolicitudIncorporacionConDetalle(BaseModel):
    id_solicitud: int
    estado: str
    observaciones: str | None
    fecha_revision: date | None
    created_at: datetime
    id_alumno: int | None
    alumno_nombre: str | None = None
    alumno_apellido: str | None = None
    alumno_ci: str | None = None
    id_programa_version_edicion: int | None
    edicion_numero: int | None = None
    edicion_anio: int | None = None
    edicion_semestre: int | None = None
    programa_nombre: str | None = None
    id_detalle_programa_alumno: int | None = None
    dpa_estado: str | None = None
    es_migracion: bool = False
    documentos: list[SolicitudDocumentoResponse] = []

    model_config = ConfigDict(from_attributes=True)
