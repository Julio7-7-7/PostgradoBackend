from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class SolicitudIncorporacionCreate(BaseModel):
    id_programa_version_edicion: int | None = None
    id_modalidad_academica: int | None = None
    id_tipo_descuento: int | None = None
    modulo_inicio: int = 1
    url_documento: str
    id_requisito: int | None = None


class AprobarSolicitudRequest(BaseModel):
    id_programa_version_edicion: int | None = None
    id_modalidad_academica: int | None = None
    id_tipo_descuento: int | None = None
    modulo_inicio: int = 1


class SolicitudIncorporacionResponse(BaseModel):
    id_solicitud: int
    id_detalle_programa_alumno: int | None
    id_alumno: int | None
    id_programa_version_edicion: int | None
    id_requisito: int | None
    tipo_documento: str
    estado: str
    url_documento: str | None
    observaciones: str | None
    fecha_entrega: date | None
    fecha_revision: date | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SolicitudIncorporacionConDetalle(BaseModel):
    id_solicitud: int
    tipo_documento: str
    estado: str
    url_documento: str | None
    observaciones: str | None
    fecha_entrega: date | None
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
    id_requisito: int | None
    requisito_nombre: str | None = None
    id_detalle_programa_alumno: int | None = None
    dpa_estado: str | None = None
    es_migracion: bool = False

    model_config = ConfigDict(from_attributes=True)
