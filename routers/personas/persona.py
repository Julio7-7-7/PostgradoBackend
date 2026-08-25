from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from database import get_db
from models.usuario import Usuario
from models.usuario_rol import UsuarioRol
from models.rol import Rol
from schemas.persona import PersonaResponse, PaginatedPersonasResponse, RolInfo
from dependencies import get_current_user, require_permiso
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/personas",
    tags=["Personas"],
    dependencies=[Depends(get_current_user)],
)


def _cargar_roles_map(db: Session, usuarios: list) -> dict:
    ur_ids = [ur.id_rol for u in usuarios for ur in u.usuario_roles if ur.id_rol]
    if not ur_ids:
        return {}
    return {r.id_rol: r for r in db.query(Rol).filter(Rol.id_rol.in_(set(ur_ids))).all()}


def _persona_response(usuario: Usuario, roles_map: dict) -> PersonaResponse:
    roles = []
    for ur in usuario.usuario_roles:
        rol = roles_map.get(ur.id_rol)
        if rol:
            roles.append(RolInfo(id_rol=rol.id_rol, nombre=rol.nombre, descripcion=rol.descripcion))

    return PersonaResponse(
        id_usuario=usuario.id_usuario,
        email=usuario.email,
        activo=usuario.activo,
        roles=roles,
        alumno=usuario.alumno,
        docente=usuario.docente,
        administrativo=usuario.administrativo,
        created_at=usuario.created_at,
    )


@router.get("", response_model=PaginatedPersonasResponse)
def listar_personas(
    q: str | None = None,
    rol: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    query = db.query(Usuario).options(
        joinedload(Usuario.usuario_roles),
        joinedload(Usuario.alumno),
        joinedload(Usuario.docente),
        joinedload(Usuario.administrativo),
    )

    if q:
        patron = f"%{q.strip()}%"
        query = query.outerjoin(Usuario.alumno).outerjoin(Usuario.docente).outerjoin(Usuario.administrativo).filter(
            or_(
                Usuario.email.ilike(patron),
                Usuario.alumno.has(nombre=patron),
                Usuario.alumno.has(apellido=patron),
                Usuario.alumno.has(ci=patron),
                Usuario.docente.has(nombre=patron),
                Usuario.docente.has(apellido=patron),
                Usuario.docente.has(ci=patron),
                Usuario.administrativo.has(nombre=patron),
                Usuario.administrativo.has(apellido=patron),
                Usuario.administrativo.has(ci=patron),
            )
        )

    if rol:
        query = query.join(Usuario.usuario_roles).join(Rol).filter(Rol.nombre == rol)

    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages

    usuarios = query.order_by(Usuario.id_usuario).offset((page - 1) * per_page).limit(per_page).all()
    roles_map = _cargar_roles_map(db, usuarios)

    return PaginatedPersonasResponse(
        items=[_persona_response(u, roles_map) for u in usuarios],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{id_usuario}", response_model=PersonaResponse)
def obtener_persona(
    id_usuario: int,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("usuarios.gestionar")),
):
    usuario = db.query(Usuario).options(
        joinedload(Usuario.usuario_roles),
        joinedload(Usuario.alumno),
        joinedload(Usuario.docente),
        joinedload(Usuario.administrativo),
    ).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Persona no encontrada")

    roles_map = _cargar_roles_map(db, [usuario])
    return _persona_response(usuario, roles_map)
