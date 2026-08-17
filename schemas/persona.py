from pydantic import BaseModel, ConfigDict
from datetime import datetime, date


class AlumnoInfo(BaseModel):
    id_alumno: int
    ci: str | None = None
    pasaporte: str | None = None
    nombre: str
    apellido: str
    correo: str
    genero: str | None = None
    celular: str | None = None
    fecha_nacimiento: date | None = None
    direccion: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DocenteInfo(BaseModel):
    id_docente: int
    ci: str
    nombre: str
    apellido: str
    correo: str
    genero: str | None = None
    celular: str | None = None
    extension: str | None = None
    grado: str | None = None
    titulo: str | None = None
    estado: str

    model_config = ConfigDict(from_attributes=True)


class AdministrativoInfo(BaseModel):
    id_administrativo: int
    ci: str
    nombre: str
    apellido: str
    correo: str | None = None
    celular: str | None = None
    cargo: str | None = None
    estado: str

    model_config = ConfigDict(from_attributes=True)


class RolInfo(BaseModel):
    id_rol: int
    nombre: str
    descripcion: str | None = None


class PersonaResponse(BaseModel):
    id_usuario: int
    email: str
    activo: bool
    roles: list[RolInfo]
    alumno: AlumnoInfo | None = None
    docente: DocenteInfo | None = None
    administrativo: AdministrativoInfo | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedPersonasResponse(BaseModel):
    items: list[PersonaResponse]
    total: int
    page: int
    per_page: int
    pages: int
