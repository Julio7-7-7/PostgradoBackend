from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.usuario import Usuario
from models.usuario_rol import UsuarioRol
from models.rol import Rol
from models.alumno import Alumno
from models.docente import Docente
from models.administrativo import Administrativo
from schemas.admin import UserAdminResponse, UserAdminCreate, UserUpdateRoles
from dependencies import get_current_user, require_permiso
from schemas.auth import UserResponse
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def _profile_info(usuario: Usuario) -> tuple[str | None, str | None]:
    if usuario.alumno:
        return "alumno", f"{usuario.alumno.nombre} {usuario.alumno.apellido}"
    if usuario.docente:
        return "docente", f"{usuario.docente.nombre} {usuario.docente.apellido}"
    if usuario.administrativo:
        return "administrativo", f"{usuario.administrativo.nombre} {usuario.administrativo.apellido}"
    return None, None


def _roles_info(usuario: Usuario) -> tuple[list[str], list[int]]:
    nombres = [ur.rol.nombre for ur in usuario.usuario_roles if ur.rol]
    ids = [ur.rol.id_rol for ur in usuario.usuario_roles if ur.rol]
    return nombres, ids


@router.get("", response_model=list[UserAdminResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    usuarios = db.query(Usuario).order_by(Usuario.id_usuario).all()
    result = []
    for u in usuarios:
        profile_type, profile_nombre = _profile_info(u)
        roles_nombres, roles_ids = _roles_info(u)
        result.append(UserAdminResponse(
            id_usuario=u.id_usuario,
            email=u.email,
            activo=u.activo,
            roles=roles_nombres,
            id_roles=roles_ids,
            profile_type=profile_type,
            profile_nombre=profile_nombre,
            created_at=u.created_at,
        ))
    return result


@router.get("/{id_usuario}", response_model=UserAdminResponse)
def obtener_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    profile_type, profile_nombre = _profile_info(usuario)
    roles_nombres, roles_ids = _roles_info(usuario)
    return UserAdminResponse(
        id_usuario=usuario.id_usuario,
        email=usuario.email,
        activo=usuario.activo,
        roles=roles_nombres,
        id_roles=roles_ids,
        profile_type=profile_type,
        profile_nombre=profile_nombre,
        created_at=usuario.created_at,
    )


@router.post("", response_model=UserAdminResponse, status_code=201)
def crear_usuario(
    data: UserAdminCreate,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    existing = db.query(Usuario).filter(Usuario.email == data.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")

    usuario = Usuario(
        email=data.email.strip().lower(),
        password_hash=pwd_context.hash(data.password),
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    for id_rol in data.roles:
        rol = db.query(Rol).filter(Rol.id_rol == id_rol).first()
        if not rol:
            raise HTTPException(status_code=400, detail=f"Rol {id_rol} no encontrado")
        db.add(UsuarioRol(id_usuario=usuario.id_usuario, id_rol=id_rol))
    db.commit()

    perfil_creado = False
    for id_rol in data.roles:
        rol = db.query(Rol).filter(Rol.id_rol == id_rol).first()
        if rol.nombre == "alumno" and not perfil_creado:
            db.add(Alumno(
                ci=data.ci, nombre=data.nombre, apellido=data.apellido,
                celular=data.celular, correo=data.email, id_usuario=usuario.id_usuario,
            ))
            perfil_creado = True
        elif rol.nombre == "docente" and not perfil_creado:
            db.add(Docente(
                ci=data.ci, nombre=data.nombre, apellido=data.apellido,
                celular=data.celular, correo=data.email, id_usuario=usuario.id_usuario,
            ))
            perfil_creado = True
        elif not perfil_creado:
            db.add(Administrativo(
                ci=data.ci, nombre=data.nombre, apellido=data.apellido,
                celular=data.celular, correo=data.email,
                cargo=rol.nombre, id_usuario=usuario.id_usuario,
            ))
            perfil_creado = True
    db.commit()
    db.refresh(usuario)

    profile_type, profile_nombre = _profile_info(usuario)
    roles_nombres, roles_ids = _roles_info(usuario)
    return UserAdminResponse(
        id_usuario=usuario.id_usuario,
        email=usuario.email,
        activo=usuario.activo,
        roles=roles_nombres,
        id_roles=roles_ids,
        profile_type=profile_type,
        profile_nombre=profile_nombre,
        created_at=usuario.created_at,
    )


@router.put("/{id_usuario}/roles")
def actualizar_roles_usuario(
    id_usuario: int,
    data: UserUpdateRoles,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    db.query(UsuarioRol).filter(UsuarioRol.id_usuario == id_usuario).delete()

    for id_rol in data.roles:
        rol = db.query(Rol).filter(Rol.id_rol == id_rol).first()
        if not rol:
            raise HTTPException(status_code=400, detail=f"Rol {id_rol} no encontrado")
        db.add(UsuarioRol(id_usuario=id_usuario, id_rol=id_rol))

    db.commit()
    return {"detail": "Roles actualizados"}


@router.put("/{id_usuario}/activo")
def toggle_activo_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    usuario.activo = not usuario.activo
    db.commit()
    return {"activo": usuario.activo, "detail": "Estado actualizado"}
