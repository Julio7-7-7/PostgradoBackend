from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_permiso
from models.alumno import Alumno
from models.usuario import Usuario
from models.usuario_rol import UsuarioRol
from models.rol import Rol
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.programa_version_edicion import ProgramaVersionEdicion
from schemas.alumno import AlumnoCreate, AlumnoUpdate, AlumnoResponse, AlumnoConUsuarioCreate
from schemas.admin import UserAdminResponse
from schemas.auth import UserResponse
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(
    prefix="/alumnos",
    tags=["Alumnos"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/", response_model=AlumnoResponse, status_code=201)
def crear(data: AlumnoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.crear"))):
    if data.ci:
        if db.query(Alumno).filter(Alumno.ci == data.ci).first():
            raise HTTPException(status_code=400, detail="Ya existe un alumno con ese CI")
    if data.pasaporte:
        if db.query(Alumno).filter(Alumno.pasaporte == data.pasaporte).first():
            raise HTTPException(status_code=400, detail="Ya existe un alumno con ese pasaporte")
    if db.query(Alumno).filter(Alumno.correo == data.correo).first():
        raise HTTPException(status_code=400, detail="Ya existe un alumno con ese correo")
    nuevo = Alumno(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.post("/crear-con-usuario", response_model=UserAdminResponse, status_code=201)
def crear_con_usuario(
    data: AlumnoConUsuarioCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.crear")),
):
    email_norm = data.email.strip().lower()
    ci_norm = data.ci.strip()

    if db.query(Usuario).filter(Usuario.email == email_norm).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")
    if db.query(Alumno).filter(Alumno.ci == ci_norm).first():
        raise HTTPException(status_code=400, detail="Ya existe un alumno con ese CI")
    if db.query(Alumno).filter(Alumno.correo == email_norm).first():
        raise HTTPException(status_code=400, detail="Ya existe un alumno con ese correo")

    password_inicial = ci_norm
    usuario = Usuario(
        email=email_norm,
        password_hash=pwd_context.hash(ci_norm),
        activo=True,
        must_change_password=True,
    )
    db.add(usuario)
    db.flush()

    rol_alumno = db.query(Rol).filter(Rol.nombre == "alumno").first()
    if rol_alumno:
        db.add(UsuarioRol(id_usuario=usuario.id_usuario, id_rol=rol_alumno.id_rol))

    db.add(Alumno(
        ci=ci_norm,
        nombre=data.nombre.strip(),
        apellido=data.apellido.strip(),
        celular=data.celular,
        correo=email_norm,
        fecha_nacimiento=data.fecha_nacimiento,
        genero=data.genero,
        id_usuario=usuario.id_usuario,
    ))

    db.commit()
    db.refresh(usuario)

    roles_nombres = [ur.rol.nombre for ur in usuario.usuario_roles if ur.rol]
    roles_ids = [ur.rol.id_rol for ur in usuario.usuario_roles if ur.rol]
    perfiles = []
    if usuario.alumno:
        perfiles.append({
            "type": "alumno",
            "id": usuario.alumno.id_alumno,
            "nombre": f"{usuario.alumno.nombre} {usuario.alumno.apellido}",
        })

    resp = UserAdminResponse(
        id_usuario=usuario.id_usuario,
        email=usuario.email,
        activo=usuario.activo,
        roles=roles_nombres,
        id_roles=roles_ids,
        perfiles=perfiles,
        created_at=usuario.created_at,
    )
    resp.password_inicial = password_inicial
    return resp


@router.get("/", response_model=list[AlumnoResponse])
def listar(db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.ver"))):
    return db.query(Alumno).all()


@router.get("/por-periodo", response_model=list[AlumnoResponse])
def listar_por_periodo(
    anio: int = Query(..., description="Año del período"),
    semestre: int | None = Query(None, description="Semestre (1 o 2)"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.ver"))
):
    ids_detalles = db.query(DetalleProgramaAlumno.id_alumno).join(
        ProgramaVersionEdicion,
        DetalleProgramaAlumno.id_programa_version_edicion == ProgramaVersionEdicion.id_programa_version_edicion
    ).filter(
        ProgramaVersionEdicion.anio == anio
    )
    if semestre is not None:
        ids_detalles = ids_detalles.filter(ProgramaVersionEdicion.semestre == semestre)

    ids_alumnos = [r[0] for r in ids_detalles.all()]
    if not ids_alumnos:
        return []

    return db.query(Alumno).filter(Alumno.id_alumno.in_(ids_alumnos)).all()


@router.get("/mi-perfil", response_model=AlumnoResponse)
def mi_perfil(db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")
    alumno = db.query(Alumno).filter(Alumno.id_alumno == current_user.id_profile).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="Perfil de alumno no encontrado")
    return alumno


@router.get("/{id}", response_model=AlumnoResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.ver"))):
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="No encontrado")
    return alumno


@router.patch("/{id}", response_model=AlumnoResponse)
def editar(id: int, data: AlumnoUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("alumnos.editar"))):
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="No encontrado")
    if data.ci:
        if db.query(Alumno).filter(Alumno.ci == data.ci, Alumno.id_alumno != id).first():
            raise HTTPException(status_code=400, detail="Ya existe un alumno con ese CI")
    if data.pasaporte:
        if db.query(Alumno).filter(Alumno.pasaporte == data.pasaporte, Alumno.id_alumno != id).first():
            raise HTTPException(status_code=400, detail="Ya existe un alumno con ese pasaporte")
    if data.correo:
        if db.query(Alumno).filter(Alumno.correo == data.correo, Alumno.id_alumno != id).first():
            raise HTTPException(status_code=400, detail="Ya existe un alumno con ese correo")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(alumno, key, value)
    db.commit()
    db.refresh(alumno)
    return alumno
