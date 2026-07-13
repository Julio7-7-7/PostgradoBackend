from fastapi import APIRouter, Depends, HTTPException, status, Request
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
    MeResponse, LoginStep1Response, RolInfo, RegistroRequest,
    CambiarPasswordRequest,
)
from dependencies import (
    create_access_token, get_current_user, _obtener_permisos,
    _obtener_profile_info, _obtener_roles_usuario
)
from rate_limiter import check_rate_limit, record_failed_attempt, clear_attempts
from passlib.context import CryptContext
from fastapi import Request as Req

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginStep1Response)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request)

    usuario = db.query(Usuario).filter(
        Usuario.email == data.email.strip().lower(),
    ).first()

    if not usuario or not pwd_context.verify(data.password, usuario.password_hash):
        record_failed_attempt(request)
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

    clear_attempts(request)

    return LoginStep1Response(
        id_usuario=usuario.id_usuario,
        email=usuario.email,
        roles=roles,
    )


@router.post("/registro", response_model=TokenResponse, status_code=201)
def registro(data: RegistroRequest, db: Session = Depends(get_db)):
    if data.honeypot:
        raise HTTPException(status_code=400, detail="Registro inválido")

    email_normalized = data.email.strip().lower()

    existing = db.query(Usuario).filter(Usuario.email == email_normalized).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese correo electrónico")

    ci_duplicada = db.query(Alumno).filter(Alumno.ci == data.ci.strip()).first()
    if ci_duplicada:
        raise HTTPException(status_code=400, detail="Ya existe un alumno registrado con esa CI")

    rol_alumno = db.query(Rol).filter(Rol.nombre == "alumno").first()
    if not rol_alumno:
        raise HTTPException(status_code=500, detail="Rol 'alumno' no encontrado en el sistema")

    try:
        usuario = Usuario(
            email=email_normalized,
            password_hash=pwd_context.hash(data.password),
            activo=True,
        )
        db.add(usuario)
        db.flush()

        db.add(UsuarioRol(id_usuario=usuario.id_usuario, id_rol=rol_alumno.id_rol))

        db.add(Alumno(
            ci=data.ci.strip(),
            nombre="Pendiente",
            apellido="Pendiente",
            correo=email_normalized,
            id_usuario=usuario.id_usuario,
        ))

        db.commit()
        db.refresh(usuario)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear la cuenta")

    permisos = _obtener_permisos(db, rol_alumno.id_rol)
    id_profile, profile_type = _obtener_profile_info(db, usuario, "alumno")
    roles_disponibles = _obtener_roles_usuario(db, usuario.id_usuario)

    user_resp = UserResponse(
        id_usuario=usuario.id_usuario,
        email=usuario.email,
        activo=usuario.activo,
        rol=rol_alumno.nombre,
        id_rol=rol_alumno.id_rol,
        id_profile=id_profile,
        profile_type=profile_type,
        permisos=permisos,
        roles=roles_disponibles,
    )

    token = create_access_token({"id_usuario": usuario.id_usuario, "id_rol": rol_alumno.id_rol})
    return TokenResponse(access_token=token, user=user_resp)


@router.post("/seleccionar-rol", response_model=TokenResponse)
def seleccionar_rol(data: SelectRolRequest, db: Session = Depends(get_db)):
    usuario_rol = db.query(UsuarioRol).filter(
        UsuarioRol.id_usuario == data.id_usuario,
        UsuarioRol.id_rol == data.id_rol,
    ).first()

    if not usuario_rol:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Rol no válido para este usuario",
        )

    usuario = db.query(Usuario).filter(
        Usuario.id_usuario == data.id_usuario,
        Usuario.activo == True,
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    permisos = _obtener_permisos(db, data.id_rol)
    id_profile, profile_type = _obtener_profile_info(db, usuario, usuario_rol.rol.nombre)
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


@router.patch("/cambiar-password")
def cambiar_password(
    data: CambiarPasswordRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == current_user.id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not pwd_context.verify(data.password_actual, usuario.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")

    if data.password_actual == data.password_nuevo:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe ser diferente a la actual")

    usuario.password_hash = pwd_context.hash(data.password_nuevo)
    db.commit()
    return {"detail": "Contraseña actualizada correctamente"}


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
