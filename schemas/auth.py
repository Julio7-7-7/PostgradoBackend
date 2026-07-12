from pydantic import BaseModel, ConfigDict
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


class SelectRolRequest(BaseModel):
    id_rol: int


class RolInfo(BaseModel):
    id_rol: int
    nombre: str
    descripcion: str | None = None

    model_config = ConfigDict(from_attributes=True)


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
    id_rol: int
    id_profile: int | None = None
    profile_type: str | None = None
    permisos: list[PermisoInfo] = []
    roles: list[RolInfo] = []

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginStep1Response(BaseModel):
    id_usuario: int
    email: str
    roles: list[RolInfo]


class MeResponse(BaseModel):
    id_usuario: int
    email: str
    activo: bool
    rol: str
    permisos: list[PermisoInfo]
    roles: list[RolInfo]
    profile: dict | None = None

    model_config = ConfigDict(from_attributes=True)
