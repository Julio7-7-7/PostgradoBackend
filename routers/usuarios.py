from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.usuario import Usuario
from models.usuario_rol import UsuarioRol
from models.rol import Rol
from models.alumno import Alumno
from models.docente import Docente
from models.administrativo import Administrativo
from schemas.admin import UserAdminResponse, UserAdminCreate, UserAdminUpdate, UserUpdateRoles, ProfileInfo, PaginatedUsersResponse
from dependencies import get_current_user, require_permiso
from schemas.auth import UserResponse
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/usuarios", tags=["Usuarios"], dependencies=[Depends(get_current_user)])


def _perfiles_info(usuario: Usuario) -> list[ProfileInfo]:
    perfiles = []
    if usuario.alumno:
        perfiles.append(ProfileInfo(
            type="alumno",
            id=usuario.alumno.id_alumno,
            nombre=f"{usuario.alumno.nombre} {usuario.alumno.apellido}",
        ))
    if usuario.docente:
        perfiles.append(ProfileInfo(
            type="docente",
            id=usuario.docente.id_docente,
            nombre=f"{usuario.docente.nombre} {usuario.docente.apellido}",
        ))
    if usuario.administrativo:
        perfiles.append(ProfileInfo(
            type="administrativo",
            id=usuario.administrativo.id_administrativo,
            nombre=f"{usuario.administrativo.nombre} {usuario.administrativo.apellido}",
        ))
    return perfiles


def _roles_info(usuario: Usuario) -> tuple[list[str], list[int]]:
    nombres = [ur.rol.nombre for ur in usuario.usuario_roles if ur.rol]
    ids = [ur.rol.id_rol for ur in usuario.usuario_roles if ur.rol]
    return nombres, ids


def _usuario_a_response(usuario: Usuario) -> UserAdminResponse:
    roles_nombres, roles_ids = _roles_info(usuario)
    perfiles = _perfiles_info(usuario)
    return UserAdminResponse(
        id_usuario=usuario.id_usuario,
        email=usuario.email,
        activo=usuario.activo,
        roles=roles_nombres,
        id_roles=roles_ids,
        perfiles=perfiles,
        created_at=usuario.created_at,
    )


def _es_unico_admin_informatico(db: Session, id_usuario: int) -> bool:
    rol_informatico = db.query(Rol).filter(Rol.nombre == "adm_informatico").first()
    if not rol_informatico:
        return False
    count = (
        db.query(UsuarioRol)
        .filter(UsuarioRol.id_rol == rol_informatico.id_rol, UsuarioRol.rol_activo == True)
        .count()
    )
    if count > 1:
        return False
    if count == 1:
        ur = db.query(UsuarioRol).filter(
            UsuarioRol.id_rol == rol_informatico.id_rol,
            UsuarioRol.rol_activo == True,
        ).first()
        return ur.id_usuario == id_usuario
    return False


@router.get("", response_model=PaginatedUsersResponse)
def listar_usuarios(
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    if per_page < 1:
        per_page = 20
    if per_page > 100:
        per_page = 100
    if page < 1:
        page = 1

    total = db.query(Usuario).count()
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages

    offset = (page - 1) * per_page
    usuarios = db.query(Usuario).order_by(Usuario.id_usuario).offset(offset).limit(per_page).all()

    return PaginatedUsersResponse(
        items=[_usuario_a_response(u) for u in usuarios],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{id_usuario}", response_model=UserAdminResponse)
def obtener_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _usuario_a_response(usuario)


@router.post("", response_model=UserAdminResponse, status_code=201)
def crear_usuario(
    data: UserAdminCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    existing = db.query(Usuario).filter(Usuario.email == data.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")

    if data.ci:
        for Model, label in [(Alumno, "alumno"), (Docente, "docente"), (Administrativo, "administrativo")]:
            dup = db.query(Model).filter(Model.ci == data.ci.strip()).first()
            if dup:
                raise HTTPException(status_code=400, detail=f"La CI ya está registrada en perfiles de tipo {label}")

    try:
        usuario = Usuario(
            email=data.email.strip().lower(),
            password_hash=pwd_context.hash(data.password),
            activo=True,
        )
        db.add(usuario)
        db.flush()

        tiene_alumno = False
        for id_rol in data.roles:
            rol = db.query(Rol).filter(Rol.id_rol == id_rol).first()
            if not rol:
                db.rollback()
                raise HTTPException(status_code=400, detail=f"Rol {id_rol} no encontrado")
            db.add(UsuarioRol(id_usuario=usuario.id_usuario, id_rol=id_rol))
            if rol.nombre == "alumno":
                tiene_alumno = True

        if not tiene_alumno:
            rol_alumno = db.query(Rol).filter(Rol.nombre == "alumno").first()
            if rol_alumno:
                db.add(UsuarioRol(id_usuario=usuario.id_usuario, id_rol=rol_alumno.id_rol))

        db.flush()

        if data.ci:
            if tiene_alumno or not any(
                db.query(Rol).filter(Rol.id_rol == id_rol).first().nombre == "alumno"
                for id_rol in data.roles
                if db.query(Rol).filter(Rol.id_rol == id_rol).first()
            ):
                pass

            ya_tiene_alumno = db.query(Alumno).filter(Alumno.id_usuario == usuario.id_usuario).first()
            if not ya_tiene_alumno:
                db.add(Alumno(
                    ci=data.ci.strip(),
                    nombre=data.nombre.strip(),
                    apellido=data.apellido.strip(),
                    celular=data.celular,
                    correo=data.email.strip().lower(),
                    id_usuario=usuario.id_usuario,
                ))

            for id_rol in data.roles:
                rol = db.query(Rol).filter(Rol.id_rol == id_rol).first()
                if not rol:
                    continue
                if rol.nombre == "docente":
                    ya_tiene = db.query(Docente).filter(Docente.id_usuario == usuario.id_usuario).first()
                    if not ya_tiene:
                        db.add(Docente(
                            ci=data.ci.strip(),
                            nombre=data.nombre.strip(),
                            apellido=data.apellido.strip(),
                            celular=data.celular,
                            correo=data.email.strip().lower(),
                            id_usuario=usuario.id_usuario,
                        ))
                elif rol.nombre not in ("alumno", "docente"):
                    ya_tiene = db.query(Administrativo).filter(Administrativo.id_usuario == usuario.id_usuario).first()
                    if not ya_tiene:
                        db.add(Administrativo(
                            ci=data.ci.strip(),
                            nombre=data.nombre.strip(),
                            apellido=data.apellido.strip(),
                            celular=data.celular,
                            correo=data.email.strip().lower(),
                            cargo=rol.nombre,
                            id_usuario=usuario.id_usuario,
                        ))

        db.commit()
        db.refresh(usuario)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear el usuario")

    return _usuario_a_response(usuario)


@router.patch("/{id_usuario}", response_model=UserAdminResponse)
def editar_usuario(
    id_usuario: int,
    data: UserAdminUpdate,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if data.email:
        email_normalized = data.email.strip().lower()
        existing = db.query(Usuario).filter(
            Usuario.email == email_normalized,
            Usuario.id_usuario != id_usuario,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe otro usuario con ese email")
        usuario.email = email_normalized

    if data.password:
        usuario.password_hash = pwd_context.hash(data.password)

    if data.ci:
        ci = data.ci.strip()
        for Model, label in [(Alumno, "alumno"), (Docente, "docente"), (Administrativo, "administrativo")]:
            dup = db.query(Model).filter(Model.ci == ci, Model.id_usuario != id_usuario).first()
            if dup:
                raise HTTPException(status_code=400, detail=f"La CI ya está registrada en perfiles de tipo {label}")

    try:
        if usuario.alumno:
            if data.ci:
                usuario.alumno.ci = data.ci.strip()
            if data.nombre:
                usuario.alumno.nombre = data.nombre.strip()
            if data.apellido:
                usuario.alumno.apellido = data.apellido.strip()
            if data.celular is not None:
                usuario.alumno.celular = data.celular

        if usuario.docente:
            if data.ci:
                usuario.docente.ci = data.ci.strip()
            if data.nombre:
                usuario.docente.nombre = data.nombre.strip()
            if data.apellido:
                usuario.docente.apellido = data.apellido.strip()
            if data.celular is not None:
                usuario.docente.celular = data.celular

        if usuario.administrativo:
            if data.ci:
                usuario.administrativo.ci = data.ci.strip()
            if data.nombre:
                usuario.administrativo.nombre = data.nombre.strip()
            if data.apellido:
                usuario.administrativo.apellido = data.apellido.strip()
            if data.celular is not None:
                usuario.administrativo.celular = data.celular
            if data.cargo is not None:
                usuario.administrativo.cargo = data.cargo

        db.commit()
        db.refresh(usuario)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar el usuario")

    return _usuario_a_response(usuario)


@router.put("/{id_usuario}/roles")
def actualizar_roles_usuario(
    id_usuario: int,
    data: UserUpdateRoles,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if id_usuario == current_user.id_usuario:
        raise HTTPException(status_code=400, detail="No podés cambiar tus propios roles desde aquí")

    tiene_alumno = any(
        db.query(Rol).filter(Rol.id_rol == id_rol).first().nombre == "alumno"
        for id_rol in data.roles
        if db.query(Rol).filter(Rol.id_rol == id_rol).first()
    )
    if not tiene_alumno:
        raise HTTPException(status_code=400, detail="Todo usuario debe mantener el rol de estudiante como base")

    try:
        db.query(UsuarioRol).filter(UsuarioRol.id_usuario == id_usuario).delete()

        for id_rol in data.roles:
            rol = db.query(Rol).filter(Rol.id_rol == id_rol).first()
            if not rol:
                db.rollback()
                raise HTTPException(status_code=400, detail=f"Rol {id_rol} no encontrado")
            db.add(UsuarioRol(id_usuario=id_usuario, id_rol=id_rol))

        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar roles")

    return {"detail": "Roles actualizados"}


@router.put("/{id_usuario}/activo")
def toggle_activo_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if id_usuario == current_user.id_usuario:
        raise HTTPException(status_code=400, detail="No podés desactivarte a ti mismo")

    if usuario.activo and _es_unico_admin_informatico(db, id_usuario):
        raise HTTPException(status_code=400, detail="No podés desactivar al único administrador informático activo")

    usuario.activo = not usuario.activo
    db.commit()
    return {"activo": usuario.activo, "detail": "Estado actualizado"}
