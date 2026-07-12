from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.usuario import Usuario
from models.usuario_rol import UsuarioRol
from models.rol import Rol
from models.alumno import Alumno
from models.docente import Docente
from models.administrativo import Administrativo
from schemas.auth import (
    LoginRequest, SelectRolRequest, TokenResponse, UserResponse,
    MeResponse, LoginStep1Response, RolInfo
)
from dependencies import (
    create_access_token, get_current_user, _obtener_permisos,
    _obtener_profile_info, _obtener_roles_usuario
)
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginStep1Response)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(
        Usuario.email == data.email.strip().lower(),
    ).first()

    if not usuario or not pwd_context.verify(data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo",
        )

    roles = _obtener_roles_usuario(db, usuario.id_usuario)
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario sin roles asignados",
        )

    return LoginStep1Response(
        id_usuario=usuario.id_usuario,
        email=usuario.email,
        roles=roles,
    )


@router.post("/seleccionar-rol", response_model=TokenResponse)
def seleccionar_rol(data: SelectRolRequest, db: Session = Depends(get_db)):
    usuario_rol = db.query(UsuarioRol).filter(
        UsuarioRol.id_rol == data.id_rol,
    ).first()

    if not usuario_rol:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Rol no válido",
        )

    usuario = db.query(Usuario).filter(
        Usuario.id_usuario == usuario_rol.id_usuario,
        Usuario.activo == True,
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    permisos = _obtener_permisos(db, data.id_rol)
    id_profile, profile_type = _obtener_profile_info(db, usuario)
    roles_disponibles = _obtener_roles_usuario(db, usuario.id_usuario)
    rol = db.query(Rol).filter(Rol.id_rol == data.id_rol).first()

    user_resp = UserResponse(
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

    token = create_access_token({"id_usuario": usuario.id_usuario, "id_rol": data.id_rol})
    return TokenResponse(access_token=token, user=user_resp)


@router.get("/roles")
def listar_roles(db: Session = Depends(get_db)):
    roles = db.query(Rol).order_by(Rol.id_rol).all()
    return [{"id_rol": r.id_rol, "nombre": r.nombre, "descripcion": r.descripcion} for r in roles]


@router.get("/me", response_model=MeResponse)
def me(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = None
    if current_user.id_profile and current_user.profile_type:
        if current_user.profile_type == "alumno":
            alumno = db.query(Alumno).filter(Alumno.id_alumno == current_user.id_profile).first()
            if alumno:
                profile = {
                    "id": alumno.id_alumno,
                    "ci": alumno.ci,
                    "nombre": f"{alumno.nombre} {alumno.apellido}",
                    "correo": alumno.correo,
                    "tipo": "alumno",
                }
        elif current_user.profile_type == "docente":
            docente = db.query(Docente).filter(Docente.id_docente == current_user.id_profile).first()
            if docente:
                profile = {
                    "id": docente.id_docente,
                    "ci": docente.ci,
                    "nombre": f"{docente.nombre} {docente.apellido}",
                    "correo": docente.correo,
                    "tipo": "docente",
                }
        elif current_user.profile_type == "administrativo":
            admin = db.query(Administrativo).filter(
                Administrativo.id_administrativo == current_user.id_profile
            ).first()
            if admin:
                profile = {
                    "id": admin.id_administrativo,
                    "ci": admin.ci,
                    "nombre": f"{admin.nombre} {admin.apellido}",
                    "correo": admin.correo,
                    "cargo": admin.cargo,
                    "tipo": "administrativo",
                }

    return MeResponse(
        id_usuario=current_user.id_usuario,
        email=current_user.email,
        activo=current_user.activo,
        rol=current_user.rol,
        permisos=current_user.permisos,
        roles=current_user.roles,
        profile=profile,
    )
