from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from datetime import datetime, date
from enum import Enum
from schemas.enums import GeneroEnum


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
    id_usuario: int
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
    must_change_password: bool = False
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


class RegistroRequest(BaseModel):
    email: str
    password: str
    ci: str | None = None
    pasaporte: str | None = None
    nombre: str | None = None
    apellido: str | None = None
    fecha_nacimiento: date | None = None
    genero: GeneroEnum | None = None
    celular: str | None = None
    direccion: str | None = None
    honeypot: str | None = None

    @model_validator(mode="after")
    def validar_documento(self):
        if not self.ci and not self.pasaporte:
            raise ValueError("Debe proporcionar al menos CI o pasaporte")
        return self

    @field_validator("fecha_nacimiento", mode="before")
    @classmethod
    def parse_fecha(cls, v):
        if isinstance(v, str) and "T" in v:
            return v.split("T")[0]
        return v

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
        if v is None:
            return v
        if len(v.strip()) < 2:
            raise ValueError("Debe tener al menos 2 caracteres")
        if len(v.strip()) > 100:
            raise ValueError("No puede superar 100 caracteres")
        return v.strip().title()

    @field_validator("celular")
    @classmethod
    def validar_celular(cls, v):
        if v and len(v.strip()) < 7:
            raise ValueError("El celular debe tener al menos 7 caracteres")
        return v.strip() if v else v

    @field_validator("email")
    @classmethod
    def validar_correo(cls, v):
        if "@" not in v:
            raise ValueError("Correo inválido")
        return v.strip().lower()


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nuevo: str


class MeResponse(BaseModel):
    id_usuario: int
    email: str
    activo: bool
    rol: str
    permisos: list[PermisoInfo]
    roles: list[RolInfo]
    profile: dict | None = None

    model_config = ConfigDict(from_attributes=True)
