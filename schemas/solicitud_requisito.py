from pydantic import BaseModel, ConfigDict


class SolicitudRequisitoCreate(BaseModel):
    id_requisito: int
    obligatorio: bool = True
    tipo: str = "incorporacion"


class SolicitudRequisitoResponse(BaseModel):
    id_solicitud_requisito: int
    id_requisito: int
    obligatorio: bool
    estado: str
    tipo: str
    requisito_nombre: str | None = None

    model_config = ConfigDict(from_attributes=True)
