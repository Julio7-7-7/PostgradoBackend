from pydantic import BaseModel, model_validator
from datetime import datetime, time
from enum import Enum
from schemas.detalle_programa_modulo import DetalleProgramaModuloResponse

class DiaEnum(str, Enum):
    lunes = "lunes"
    martes = "martes"
    miercoles = "miercoles"
    jueves = "jueves"
    viernes = "viernes"
    sabado = "sabado"
    domingo = "domingo"

class HorarioBase(BaseModel):
    id_detalle_programa_modulo: int
    dia: DiaEnum
    hora_ini: time
    hora_fin: time
    aula: str | None = None

    @model_validator(mode="after")
    def validar_horas(self):
        if self.hora_fin <= self.hora_ini:
            raise ValueError("La hora fin debe ser mayor a la hora inicio")
        diferencia = datetime.combine(datetime.today(), self.hora_fin) - datetime.combine(datetime.today(), self.hora_ini)
        if diferencia.seconds < 3600:
            raise ValueError("La duración mínima del horario es 1 hora")
        return self

class HorarioCreate(HorarioBase):
    pass

class HorarioUpdate(BaseModel):
    dia: DiaEnum | None = None
    hora_ini: time | None = None
    hora_fin: time | None = None
    aula: str | None = None
    estado: str | None = None

class HorarioResponse(HorarioBase):
    id_horario: int
    estado: str
    detalle_programa_modulo: DetalleProgramaModuloResponse
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class HorarioListResponse(HorarioBase):
    id_horario: int
    estado: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True