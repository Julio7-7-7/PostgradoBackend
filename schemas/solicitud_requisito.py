from pydantic import BaseModel, ConfigDict


class SolicitudRequisitoCreate(BaseModel):
    id_requisito: int
    id_tipo_solicitud: int


class SolicitudRequisitoResponse(BaseModel):
    id_solicitud_requisito: int
    id_requisito: int
    id_tipo_solicitud: int
    estado: str
    tipo_codigo: str | None = None
    requisito_nombre: str | None = None

    model_config = ConfigDict(from_attributes=True)
