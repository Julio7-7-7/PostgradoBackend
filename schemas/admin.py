from pydantic import BaseModel, ConfigDict
from datetime import datetime


class PermisoResponse(BaseModel):
    id_permiso: int
    codigo: str
    descripcion: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RolCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    permisos: list[int] = []


class RolUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    permisos: list[int] | None = None


class RolResponse(BaseModel):
    id_rol: int
    nombre: str
    descripcion: str | None = None
    created_at: datetime
    updated_at: datetime
    permisos: list[PermisoResponse] = []

    model_config = ConfigDict(from_attributes=True)


class UserAdminResponse(BaseModel):
    id_usuario: int
    email: str
    activo: bool
    rol: str
    id_rol: int
    profile_type: str | None = None
    profile_nombre: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserAdminCreate(BaseModel):
    email: str
    password: str
    id_rol: int
    ci: str
    nombre: str
    apellido: str
    celular: str | None = None


class UserChangeRol(BaseModel):
    id_rol: int
