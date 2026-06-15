from pydantic import BaseModel, ConfigDict
from datetime import datetime
from schemas.programa import ProgramaResponse

class ProgramaVersionBase(BaseModel):
    id_programa: int
    descripcion: str | None = None
    foto: str | None = None
    vigente: bool = True

class ProgramaVersionCreate(ProgramaVersionBase):
    pass

class ProgramaVersionUpdate(BaseModel):
    descripcion: str | None = None
    foto: str | None = None
    vigente: bool | None = None

class ProgramaVersionResponse(ProgramaVersionBase):
    id_programa_version: int
    version: int
    programa: ProgramaResponse
    ediciones_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)