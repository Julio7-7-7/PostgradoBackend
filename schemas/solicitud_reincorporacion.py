from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class SolicitudReincorporacionCreate(BaseModel):
    motivo: str = ""


class SolicitudReincorporacionDocumentoResponse(BaseModel):
    id_solicitud_reincorporacion_documento: int
    id_requisito: int
    nombre_requisito: str = ""
    url_documento: str
    estado: str
    fecha_entrega: datetime

    model_config = ConfigDict(from_attributes=True)


class SolicitudReincorporacionResponse(BaseModel):
    id_solicitud_reincorporacion: int
    id_detalle_programa_alumno: int
    estado: str
    motivo: str | None
    motivo_rechazo: str | None
    created_at: datetime
    updated_at: datetime
    documentos: list[SolicitudReincorporacionDocumentoResponse] = []

    model_config = ConfigDict(from_attributes=True)


class SolicitudReincorporacionConDetalle(BaseModel):
    id_solicitud_reincorporacion: int
    estado: str
    motivo: str | None
    motivo_rechazo: str | None
    created_at: datetime
    id_alumno: int | None
    alumno_nombre: str | None = None
    alumno_apellido: str | None = None
    alumno_ci: str | None = None
    id_detalle_programa_alumno: int
    dpa_estado: str | None = None
    edicion_numero: int | None = None
    edicion_anio: int | None = None
    edicion_semestre: int | None = None
    programa_nombre: str | None = None
    documentos: list[SolicitudReincorporacionDocumentoResponse] = []

    model_config = ConfigDict(from_attributes=True)
