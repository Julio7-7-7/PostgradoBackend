from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from datetime import datetime, date
from enum import Enum

class GeneroEnum(str, Enum):
    masculino = "masculino"
    femenino = "femenino"
    otro = "otro"

class EstadoAlumnoEnum(str, Enum):
    activo = "activo"
    inactivo = "inactivo"
    graduado = "graduado"

class AlumnoBase(BaseModel):
    ci: str | None = None
    pasaporte: str | None = None
    nombre: str
    apellido: str
    fecha_nacimiento: date | None = None
    genero: GeneroEnum | None = None
    celular: str | None = None
    correo: str
    direccion: str | None = None
    estado: EstadoAlumnoEnum = EstadoAlumnoEnum.activo

    @model_validator(mode="after")
    def validar_documento(self):
        if not self.ci and not self.pasaporte:
            raise ValueError("Debe proporcionar al menos CI o pasaporte")
        return self

    @field_validator("ci")
    @classmethod
    def validar_ci(cls, v):
        if v and len(v.strip()) < 5:
            raise ValueError("El CI debe tener al menos 5 caracteres")
        return v.strip() if v else v

    @field_validator("pasaporte")
    @classmethod
    def validar_pasaporte(cls, v):
        if v and len(v.strip()) < 5:
            raise ValueError("El pasaporte debe tener al menos 5 caracteres")
        return v.strip().upper() if v else v

    @field_validator("nombre", "apellido")
    @classmethod
    def validar_nombre(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("Debe tener al menos 2 caracteres")
        if len(v.strip()) > 100:
            raise ValueError("No puede superar 100 caracteres")
        return v.strip().title()

    @field_validator("correo")
    @classmethod
    def validar_correo(cls, v):
        if "@" not in v:
            raise ValueError("Correo inválido")
        return v.strip().lower()

class AlumnoCreate(AlumnoBase):
    pass

class AlumnoUpdate(BaseModel):
    ci: str | None = None
    pasaporte: str | None = None
    nombre: str | None = None
    apellido: str | None = None
    fecha_nacimiento: date | None = None
    genero: GeneroEnum | None = None
    celular: str | None = None
    correo: str | None = None
    direccion: str | None = None
    estado: EstadoAlumnoEnum | None = None

class AlumnoResponse(AlumnoBase):
    id_alumno: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)