from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.rol import Rol
from models.permiso import Permiso
from models.roles_permiso import RolesPermiso
from models.usuario import Usuario
from models.usuario_rol import UsuarioRol
from schemas.admin import RolCreate, RolUpdate, RolResponse, PermisoResponse, BatchAsignacionesRequest
from dependencies import get_current_user, require_permiso
from schemas.auth import UserResponse

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=list[RolResponse])
def listar_roles(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("roles.gestionar")),
):
    roles = db.query(Rol).order_by(Rol.id_rol).all()
    result = []
    for r in roles:
        permisos = (
            db.query(Permiso)
            .join(RolesPermiso, RolesPermiso.id_permiso == Permiso.id_permiso)
            .filter(RolesPermiso.id_rol == r.id_rol)
            .all()
        )
        result.append(RolResponse(
            id_rol=r.id_rol,
            nombre=r.nombre,
            descripcion=r.descripcion,
            created_at=r.created_at,
            updated_at=r.updated_at,
            permisos=[PermisoResponse.model_validate(p) for p in permisos],
        ))
    return result


@router.get("/{id_rol}", response_model=RolResponse)
def obtener_rol(
    id_rol: int,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("roles.gestionar")),
):
    rol = db.query(Rol).filter(Rol.id_rol == id_rol).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    permisos = (
        db.query(Permiso)
        .join(RolesPermiso, RolesPermiso.id_permiso == Permiso.id_permiso)
        .filter(RolesPermiso.id_rol == rol.id_rol)
        .all()
    )
    return RolResponse(
        id_rol=rol.id_rol,
        nombre=rol.nombre,
        descripcion=rol.descripcion,
        created_at=rol.created_at,
        updated_at=rol.updated_at,
        permisos=[PermisoResponse.model_validate(p) for p in permisos],
    )


@router.post("", response_model=RolResponse, status_code=201)
def crear_rol(
    data: RolCreate,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("roles.gestionar")),
):
    exists = db.query(Rol).filter(Rol.nombre == data.nombre).first()
    if exists:
        raise HTTPException(status_code=400, detail="Ya existe un rol con ese nombre")
    rol = Rol(nombre=data.nombre, descripcion=data.descripcion)
    db.add(rol)
    db.commit()
    db.refresh(rol)
    if data.permisos:
        for id_permiso in data.permisos:
            permiso = db.query(Permiso).filter(Permiso.id_permiso == id_permiso).first()
            if permiso:
                db.add(RolesPermiso(id_rol=rol.id_rol, id_permiso=id_permiso))
        db.commit()
    permisos = (
        db.query(Permiso)
        .join(RolesPermiso, RolesPermiso.id_permiso == Permiso.id_permiso)
        .filter(RolesPermiso.id_rol == rol.id_rol)
        .all()
    )
    return RolResponse(
        id_rol=rol.id_rol,
        nombre=rol.nombre,
        descripcion=rol.descripcion,
        created_at=rol.created_at,
        updated_at=rol.updated_at,
        permisos=[PermisoResponse.model_validate(p) for p in permisos],
    )


@router.put("/{id_rol}", response_model=RolResponse)
def actualizar_rol(
    id_rol: int,
    data: RolUpdate,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("roles.gestionar")),
):
    rol = db.query(Rol).filter(Rol.id_rol == id_rol).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    if data.nombre is not None:
        conflict = db.query(Rol).filter(
            Rol.nombre == data.nombre, Rol.id_rol != id_rol
        ).first()
        if conflict:
            raise HTTPException(status_code=400, detail="Ya existe otro rol con ese nombre")
        rol.nombre = data.nombre
    if data.descripcion is not None:
        rol.descripcion = data.descripcion
    if data.permisos is not None:
        db.query(RolesPermiso).filter(RolesPermiso.id_rol == id_rol).delete()
        for id_permiso in data.permisos:
            permiso = db.query(Permiso).filter(Permiso.id_permiso == id_permiso).first()
            if permiso:
                db.add(RolesPermiso(id_rol=id_rol, id_permiso=id_permiso))
    db.commit()
    db.refresh(rol)
    permisos = (
        db.query(Permiso)
        .join(RolesPermiso, RolesPermiso.id_permiso == Permiso.id_permiso)
        .filter(RolesPermiso.id_rol == rol.id_rol)
        .all()
    )
    return RolResponse(
        id_rol=rol.id_rol,
        nombre=rol.nombre,
        descripcion=rol.descripcion,
        created_at=rol.created_at,
        updated_at=rol.updated_at,
        permisos=[PermisoResponse.model_validate(p) for p in permisos],
    )


@router.delete("/{id_rol}", status_code=204)
def eliminar_rol(
    id_rol: int,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("roles.gestionar")),
):
    rol = db.query(Rol).filter(Rol.id_rol == id_rol).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    tiene_usuarios = db.query(UsuarioRol).filter(UsuarioRol.id_rol == id_rol).first()
    if tiene_usuarios:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar un rol que tiene usuarios asignados",
        )
    db.query(RolesPermiso).filter(RolesPermiso.id_rol == id_rol).delete()
    db.delete(rol)
    db.commit()


@router.post("/asignaciones/batch", status_code=200)
def asignar_permisos_batch(
    data: BatchAsignacionesRequest,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_permiso("roles.gestionar")),
):
    procesados = 0
    for cambio in data.cambios:
        rol = db.query(Rol).filter(Rol.id_rol == cambio.id_rol).first()
        if not rol:
            continue
        permiso = db.query(Permiso).filter(Permiso.id_permiso == cambio.id_permiso).first()
        if not permiso:
            continue

        existente = db.query(RolesPermiso).filter(
            RolesPermiso.id_rol == cambio.id_rol,
            RolesPermiso.id_permiso == cambio.id_permiso,
        ).first()

        if cambio.asignado and not existente:
            db.add(RolesPermiso(id_rol=cambio.id_rol, id_permiso=cambio.id_permiso))
            procesados += 1
        elif not cambio.asignado and existente:
            db.delete(existente)
            procesados += 1

    db.commit()
    return {"detail": f"{procesados} cambios procesados"}
