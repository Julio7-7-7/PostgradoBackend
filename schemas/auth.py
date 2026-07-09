from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from enum import Enum


class RolEnum(str, Enum):
    adm_informatico = "adm_informatico"
    adm_legal = "adm_legal"
    adm_contable = "adm_contable"
    adm_director = "adm_director"
    adm_pasante = "adm_pasante"
    docente = "docente"
    alumno = "alumno"


class LoginRequest(BaseModel):
    email: str
    password: str
    id_rol: int


class RegisterRequest(BaseModel):
    email: str
    password: str
    id_rol: int
    ci: str
    nombre: str
    apellido: str
    celular: str | None = None

    @field_validator("email")
    @classmethod
    def validar_email(cls, v):
        if "@" not in v:
            raise ValueError("Correo inválido")
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def validar_password(cls, v):
        if len(v) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")
        return v


class PermisoInfo(BaseModel):
    id_permiso: int
    codigo: str
    descripcion: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id_usuario: int
    email: str
    activo: bool
    rol: str
    id_profile: int | None = None
    profile_type: str | None = None
    permisos: list[PermisoInfo] = []

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MeResponse(BaseModel):
    id_usuario: int
    email: str
    activo: bool
    rol: str
    permisos: list[PermisoInfo]
    profile: dict | None = None

    model_config = ConfigDict(from_attributes=True)
