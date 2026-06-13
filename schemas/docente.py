import re
from pydantic import BaseModel, field_validator
from datetime import datetime
from enum import Enum

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

class EstadoDocenteEnum(str, Enum):
    disponible = "disponible"
    contratado = "contratado"
    inactivo = "inactivo"

class GeneroEnum(str, Enum):
    masculino = "masculino"
    femenino = "femenino"
    otro = "otro"

class DocenteBase(BaseModel):
    ci: str
    nombre: str
    apellido: str
    genero: GeneroEnum | None = None
    titulo: str | None = None
    celular: str | None = None
    correo: str
    estado: EstadoDocenteEnum = EstadoDocenteEnum.disponible

    @field_validator("ci")
    @classmethod
    def validar_ci(cls, v):
        if len(v.strip()) < 5:
            raise ValueError("El CI debe tener al menos 5 caracteres")
        return v.strip()

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
        if not EMAIL_REGEX.match(v.strip()):
            raise ValueError("Correo inválido")
        return v.strip().lower()

class DocenteCreate(DocenteBase):
    pass

class DocenteUpdate(BaseModel):
    ci: str | None = None
    nombre: str | None = None
    apellido: str | None = None
    genero: GeneroEnum | None = None
    titulo: str | None = None
    celular: str | None = None
    correo: str | None = None
    estado: EstadoDocenteEnum | None = None

class DocenteResponse(DocenteBase):
    id_docente: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True