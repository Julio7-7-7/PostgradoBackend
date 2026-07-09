from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.usuario import Usuario
from models.rol import Rol
from models.alumno import Alumno
from models.docente import Docente
from models.administrativo import Administrativo
from schemas.auth import (
    LoginRequest, RegisterRequest, TokenResponse, UserResponse, MeResponse, PermisoInfo
)
from dependencies import create_access_token, get_current_user, _obtener_permisos, _obtener_profile_info
from passlib.context import CryptContext
from datetime import date

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(
        Usuario.email == data.email.strip().lower(),
        Usuario.id_rol == data.id_rol,
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

    permisos = _obtener_permisos(db, usuario.id_rol)
    id_profile, profile_type = _obtener_profile_info(db, usuario)

    user_resp = UserResponse(
        id_usuario=usuario.id_usuario,
        email=usuario.email,
        activo=usuario.activo,
        rol=usuario.rol.nombre,
        id_profile=id_profile,
        profile_type=profile_type,
        permisos=permisos,
    )

    token = create_access_token({"id_usuario": usuario.id_usuario, "id_rol": usuario.id_rol})
    return TokenResponse(access_token=token, user=user_resp)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
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
        email=data.email,
        password_hash=pwd_context.hash(data.password),
        id_rol=data.id_rol,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    if rol.nombre == "alumno":
        alumno = Alumno(
            ci=data.ci,
            nombre=data.nombre,
            apellido=data.apellido,
            celular=data.celular,
            correo=data.email,
            id_usuario=usuario.id_usuario,
        )
        db.add(alumno)
    elif rol.nombre == "docente":
        docente = Docente(
            ci=data.ci,
            nombre=data.nombre,
            apellido=data.apellido,
            celular=data.celular,
            correo=data.email,
            id_usuario=usuario.id_usuario,
        )
        db.add(docente)
    else:
        admin = Administrativo(
            ci=data.ci,
            nombre=data.nombre,
            apellido=data.apellido,
            celular=data.celular,
            correo=data.email,
            cargo=rol.nombre,
            id_usuario=usuario.id_usuario,
        )
        db.add(admin)

    db.commit()

    permisos = _obtener_permisos(db, usuario.id_rol)
    id_profile, profile_type = _obtener_profile_info(db, usuario)

    user_resp = UserResponse(
        id_usuario=usuario.id_usuario,
        email=usuario.email,
        activo=usuario.activo,
        rol=rol.nombre,
        id_profile=id_profile,
        profile_type=profile_type,
        permisos=permisos,
    )

    token = create_access_token({"id_usuario": usuario.id_usuario, "id_rol": usuario.id_rol})
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
        profile=profile,
    )
