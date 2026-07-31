from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class SolicitudCreate(BaseModel):
    id_programa_version_edicion: int | None = None
    id_modalidad_academica: int | None = None
    id_tipo_descuento: int | None = None
    motivo: str | None = None
    url_documento: str = ""
    id_requisito: int | None = None


class AprobarSolicitudRequest(BaseModel):
    id_programa_version_edicion: int | None = None
    id_tipo_descuento: int | None = None
    id_modulo_inicio: int | None = None
    motivo: str = ""


class DocumentoSolicitudResponse(BaseModel):
    id_solicitud_documento: int
    id_requisito: int
    nombre_requisito: str = ""
    url_documento: str
    estado: str
    fecha_entrega: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SolicitudIncorporacionResponse(BaseModel):
    id_solicitud: int
    id_programa_version_edicion: int
    id_modalidad_academica: int
    id_tipo_descuento: int | None = None

    model_config = ConfigDict(from_attributes=True)


class SolicitudMigracionResponse(BaseModel):
    id_solicitud: int
    id_edicion_destino: int
    motivo: str

    model_config = ConfigDict(from_attributes=True)


class SolicitudResponse(BaseModel):
    id_solicitud: int
    id_tipo_solicitud: int
    tipo_codigo: str = ""
    id_alumno: int
    id_detalle_origen: int | None = None
    estado: str
    motivo: str | None = None
    motivo_rechazo: str | None = None
    created_at: datetime
    updated_at: datetime
    documentos: list[DocumentoSolicitudResponse] = []
    incorporacion: SolicitudIncorporacionResponse | None = None
    migracion: SolicitudMigracionResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class SolicitudConDetalle(BaseModel):
    id_solicitud: int
    id_tipo_solicitud: int
    tipo_codigo: str = ""
    id_alumno: int | None = None
    alumno_nombre: str | None = None
    alumno_apellido: str | None = None
    alumno_ci: str | None = None
    estado: str
    motivo: str | None = None
    motivo_rechazo: str | None = None
    id_detalle_origen: int | None = None
    edicion_numero: int | None = None
    edicion_anio: int | None = None
    edicion_semestre: int | None = None
    programa_nombre: str | None = None
    dpa_estado: str | None = None
    created_at: datetime
    documentos: list[DocumentoSolicitudResponse] = []
    incorporacion: SolicitudIncorporacionResponse | None = None
    migracion: SolicitudMigracionResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class PreviewMigracionResponse(BaseModel):
    alumno: dict
    origen: dict
    destino: dict
    resumen: dict
