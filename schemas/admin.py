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
    roles: list[str]
    id_roles: list[int]
    profile_type: str | None = None
    profile_nombre: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserAdminCreate(BaseModel):
    email: str
    password: str
    roles: list[int]
    ci: str
    nombre: str
    apellido: str
    celular: str | None = None


class UserUpdateRoles(BaseModel):
    roles: list[int]


class BatchAsignacion(BaseModel):
    id_rol: int
    id_permiso: int
    asignado: bool


class BatchAsignacionesRequest(BaseModel):
    cambios: list[BatchAsignacion]


class AutoInscribirRequest(BaseModel):
    id_programa_version_edicion: int
    id_modalidad_academica: int
    id_tipo_descuento: int | None = None
