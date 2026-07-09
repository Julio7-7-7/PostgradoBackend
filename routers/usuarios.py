from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.usuario import Usuario
from models.rol import Rol
from models.alumno import Alumno
from models.docente import Docente
from models.administrativo import Administrativo
from schemas.admin import UserAdminResponse, UserAdminCreate, UserChangeRol
from dependencies import get_current_user, require_permiso, _obtener_permisos, _obtener_profile_info
from schemas.auth import UserResponse, TokenResponse
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


@router.get("", response_model=list[UserAdminResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    usuarios = db.query(Usuario).order_by(Usuario.id_usuario).all()
    result = []
    for u in usuarios:
        profile_type, profile_nombre = _profile_info(u)
        result.append(UserAdminResponse(
            id_usuario=u.id_usuario,
            email=u.email,
            activo=u.activo,
            rol=u.rol.nombre,
            id_rol=u.id_rol,
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
    return UserAdminResponse(
        id_usuario=usuario.id_usuario,
        email=usuario.email,
        activo=usuario.activo,
        rol=usuario.rol.nombre,
        id_rol=usuario.id_rol,
        profile_type=profile_type,
        profile_nombre=profile_nombre,
        created_at=usuario.created_at,
    )


@router.post("", response_model=TokenResponse, status_code=201)
def crear_usuario(
    data: UserAdminCreate,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    rol = db.query(Rol).filter(Rol.id_rol == data.id_rol).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    existing = db.query(Usuario).filter(
        Usuario.email == data.email,
        Usuario.id_rol == data.id_rol,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email y rol")

    usuario = Usuario(
        email=data.email.strip().lower(),
        password_hash=pwd_context.hash(data.password),
        id_rol=data.id_rol,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    if rol.nombre == "alumno":
        alumno = Alumno(
            ci=data.ci, nombre=data.nombre, apellido=data.apellido,
            celular=data.celular, correo=data.email, id_usuario=usuario.id_usuario,
        )
        db.add(alumno)
    elif rol.nombre == "docente":
        docente = Docente(
            ci=data.ci, nombre=data.nombre, apellido=data.apellido,
            celular=data.celular, correo=data.email, id_usuario=usuario.id_usuario,
        )
        db.add(docente)
    else:
        admin = Administrativo(
            ci=data.ci, nombre=data.nombre, apellido=data.apellido,
            celular=data.celular, correo=data.email,
            cargo=rol.nombre, id_usuario=usuario.id_usuario,
        )
        db.add(admin)

    db.commit()

    permisos = _obtener_permisos(db, usuario.id_rol)
    id_profile, profile_type = _obtener_profile_info(db, usuario)

    from dependencies import create_access_token
    token = create_access_token({"id_usuario": usuario.id_usuario, "id_rol": usuario.id_rol})

    user_resp = UserResponse(
        id_usuario=usuario.id_usuario,
        email=usuario.email,
        activo=usuario.activo,
        rol=rol.nombre,
        id_profile=id_profile,
        profile_type=profile_type,
        permisos=permisos,
    )
    return TokenResponse(access_token=token, user=user_resp)


@router.put("/{id_usuario}/rol")
def cambiar_rol_usuario(
    id_usuario: int,
    data: UserChangeRol,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    rol = db.query(Rol).filter(Rol.id_rol == data.id_rol).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    conflict = db.query(Usuario).filter(
        Usuario.email == usuario.email,
        Usuario.id_rol == data.id_rol,
        Usuario.id_usuario != id_usuario,
    ).first()
    if conflict:
        raise HTTPException(status_code=400, detail="Ya existe otro usuario con ese email y rol")
    usuario.id_rol = data.id_rol
    db.commit()
    return {"detail": "Rol actualizado"}


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
