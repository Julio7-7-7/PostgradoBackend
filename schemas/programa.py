from pydantic import BaseModel, field_validator
from datetime import datetime
from schemas.tipo_programa import TipoProgramaResponse, EstadoEnum

class ProgramaBase(BaseModel):
    id_tipo_programa: int
    nombre_programa: str
    foto: str | None = None
    estado: EstadoEnum = EstadoEnum.activo

    @field_validator("nombre_programa")
    @classmethod
    def validar_nombre(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres")
        if len(v.strip()) > 200:
            raise ValueError("El nombre no puede superar 200 caracteres")
        return v.strip().title()

class ProgramaCreate(ProgramaBase):
    pass

class ProgramaUpdate(BaseModel):
    id_tipo_programa: int | None = None
    nombre_programa: str | None = None
    foto: str | None = None
    estado: EstadoEnum | None = None

class ProgramaResponse(ProgramaBase):
    id_programa: int
    tipo_programa: TipoProgramaResponse
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True