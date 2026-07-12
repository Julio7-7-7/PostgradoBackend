from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from database import get_db
from models.usuario import Usuario
from models.usuario_rol import UsuarioRol
from models.rol import Rol
from models.roles_permiso import RolesPermiso
from models.permiso import Permiso
from schemas.auth import UserResponse, PermisoInfo, RolInfo
import os

security = HTTPBearer()
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-dev-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


def create_access_token(data: dict) -> str:
    from datetime import datetime, timedelta, timezone
    to_encode = data.copy()
    expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserResponse:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id_usuario: int = payload.get("id_usuario")
        id_rol: int = payload.get("id_rol")
        if id_usuario is None or id_rol is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    usuario = db.query(Usuario).filter(
        Usuario.id_usuario == id_usuario,
        Usuario.activo == True,
    ).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")

    usuario_rol = db.query(UsuarioRol).filter(
        UsuarioRol.id_usuario == id_usuario,
        UsuarioRol.id_rol == id_rol,
    ).first()
    if not usuario_rol:
        raise HTTPException(status_code=401, detail="Rol no válido para este usuario")

    rol = db.query(Rol).filter(Rol.id_rol == id_rol).first()

    permisos = _obtener_permisos(db, id_rol)
    id_profile, profile_type = _obtener_profile_info(db, usuario, rol.nombre)

    roles_disponibles = _obtener_roles_usuario(db, id_usuario)

    return UserResponse(
        id_usuario=usuario.id_usuario,
        email=usuario.email,
        activo=usuario.activo,
        rol=rol.nombre,
        id_rol=rol.id_rol,
        id_profile=id_profile,
        profile_type=profile_type,
        permisos=permisos,
        roles=roles_disponibles,
    )


def require_permiso(codigo_permiso: str):
    def dependency(current_user: UserResponse = Depends(get_current_user)):
        for p in current_user.permisos:
            if p.codigo == codigo_permiso:
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permiso denegado: se requiere '{codigo_permiso}'",
        )
    return dependency


def _obtener_permisos(db: Session, id_rol: int) -> list[PermisoInfo]:
    rows = (
        db.query(Permiso)
        .join(RolesPermiso, RolesPermiso.id_permiso == Permiso.id_permiso)
        .filter(RolesPermiso.id_rol == id_rol)
        .all()
    )
    return [PermisoInfo.model_validate(p) for p in rows]


def _obtener_roles_usuario(db: Session, id_usuario: int) -> list[RolInfo]:
    rows = (
        db.query(Rol)
        .join(UsuarioRol, UsuarioRol.id_rol == Rol.id_rol)
        .filter(UsuarioRol.id_usuario == id_usuario)
        .all()
    )
    return [RolInfo(id_rol=r.id_rol, nombre=r.nombre, descripcion=r.descripcion) for r in rows]


def _obtener_profile_info(db: Session, usuario: Usuario, nombre_rol: str) -> tuple[int | None, str | None]:
    if nombre_rol == 'alumno' and usuario.alumno:
        return usuario.alumno.id_alumno, "alumno"
    if nombre_rol == 'docente' and usuario.docente:
        return usuario.docente.id_docente, "docente"
    if nombre_rol in ('adm_informatico', 'adm_legal', 'adm_contable', 'adm_director', 'adm_pasante') and usuario.administrativo:
        return usuario.administrativo.id_administrativo, "administrativo"
    if usuario.alumno:
        return usuario.alumno.id_alumno, "alumno"
    if usuario.docente:
        return usuario.docente.id_docente, "docente"
    if usuario.administrativo:
        return usuario.administrativo.id_administrativo, "administrativo"
    return None, None
