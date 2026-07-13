from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
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
    current_user: UserResponse = Depends(require_permiso("roles.gestionar")),
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
        permiso_gestionar = db.query(Permiso).filter(Permiso.codigo == "roles.gestionar").first()
        if permiso_gestionar:
            queria_quitar = permiso_gestionar.id_permiso not in data.permisos
            tiene_usuarios = db.query(UsuarioRol).filter(UsuarioRol.id_rol == id_rol).first()
            if queria_quitar and tiene_usuarios:
                raise HTTPException(
                    status_code=400,
                    detail="No se puede quitar el permiso 'roles.gestionar' de un rol que tiene usuarios asignados",
                )
            if queria_quitar and current_user.id_rol == id_rol:
                raise HTTPException(
                    status_code=400,
                    detail="No podés quitar 'roles.gestionar' de tu propio rol activo",
                )

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
    errores = []
    for cambio in data.cambios:
        rol = db.query(Rol).filter(Rol.id_rol == cambio.id_rol).first()
        if not rol:
            errores.append(f"Rol {cambio.id_rol} no existe")
            continue
        permiso = db.query(Permiso).filter(Permiso.id_permiso == cambio.id_permiso).first()
        if not permiso:
            errores.append(f"Permiso {cambio.id_permiso} no existe")
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
    if errores:
        return {"detail": f"{procesados} cambios procesados", "errores": errores}
    return {"detail": f"{procesados} cambios procesados"}
