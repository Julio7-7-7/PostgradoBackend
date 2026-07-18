from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_permiso
from models.nota import Nota
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.alumno import Alumno
from models.modulo import Modulo
from schemas.nota import NotaCreate, NotaUpdate, NotaResponse
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/notas",
    tags=["Notas"],
    dependencies=[Depends(get_current_user)]
)


def _es_alumno_actual(usuario: UserResponse, id_alumno: int, db: Session) -> bool:
    if usuario.profile_type == "alumno" and usuario.id_profile == id_alumno:
        return True
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id_alumno).first()
    if not alumno or not alumno.id_usuario:
        return False
    return alumno.id_usuario == usuario.id_usuario


@router.get("/por-edicion/{id_edicion}")
def notas_por_edicion(
    id_edicion: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("notas.ver"))
):
    detalles_alumno = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_programa_version_edicion == id_edicion
    ).all()

    detalles_modulo = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == id_edicion
    ).all()

    modulos_map = {}
    for dm in detalles_modulo:
        mod = db.query(Modulo).filter(Modulo.id_modulo == dm.id_modulo).first()
        modulos_map[dm.id_detalle_programa_modulo] = {
            "id_detalle_programa_modulo": dm.id_detalle_programa_modulo,
            "nombre": mod.nombre_modulo if mod else f"Módulo #{dm.id_modulo}",
            "orden": dm.orden,
        }

    resultado = []
    for detalle in detalles_alumno:
        alumno = db.query(Alumno).filter(Alumno.id_alumno == detalle.id_alumno).first()
        notas = db.query(Nota).filter(
            Nota.id_detalle_programa_alumno == detalle.id_detalle_programa_alumno
        ).all()

        notas_data = []
        for n in notas:
            modulo_info = modulos_map.get(n.id_detalle_programa_modulo, {})
            notas_data.append({
                "id_nota": n.id_nota,
                "id_detalle_programa_modulo": n.id_detalle_programa_modulo,
                "modulo_nombre": modulo_info.get("nombre", "N/A"),
                "modulo_orden": modulo_info.get("orden", 0),
                "nota": float(n.nota),
                "tipo": n.tipo,
                "fecha": str(n.fecha),
                "observaciones": n.observaciones,
                "created_at": str(n.created_at),
                "updated_at": str(n.updated_at),
            })

        promedio = 0
        notas_finales = [n for n in notas_data if n["tipo"] == "final"]
        if notas_finales:
            promedio = round(sum(n["nota"] for n in notas_finales) / len(notas_finales), 2)

        resultado.append({
            "id_detalle_programa_alumno": detalle.id_detalle_programa_alumno,
            "alumno": {
                "id_alumno": alumno.id_alumno if alumno else None,
                "nombre": alumno.nombre if alumno else "N/A",
                "apellido": alumno.apellido if alumno else "N/A",
                "ci": alumno.ci if alumno else None,
            } if alumno else None,
            "notas": notas_data,
            "promedio": promedio,
        })

    return resultado


@router.get("/mis-notas/{id_detalle}")
def mis_notas(
    id_detalle: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id_detalle,
        DetalleProgramaAlumno.id_alumno == current_user.id_profile,
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    notas = db.query(Nota).filter(
        Nota.id_detalle_programa_alumno == id_detalle
    ).all()

    return {"notas": notas}


@router.post("/", response_model=NotaResponse, status_code=201)
def crear_nota(data: NotaCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("notas.subir"))):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == data.id_detalle_programa_alumno
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    dm = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == data.id_detalle_programa_modulo
    ).first()
    if not dm:
        raise HTTPException(status_code=404, detail="Módulo no encontrado")

    if float(data.nota) < 0 or float(data.nota) > 100:
        raise HTTPException(status_code=400, detail="La nota debe estar entre 0 y 100")

    if _es_alumno_actual(current_user, detalle.id_alumno, db):
        raise HTTPException(status_code=403, detail="No podés calificar tu propia inscripción")

    nuevo = Nota(**data.model_dump())
    db.add(nuevo)
    db.flush()
    db.refresh(nuevo)
    return nuevo


@router.patch("/{id}", response_model=NotaResponse)
def editar_nota(
    id: int,
    data: NotaUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("notas.subir"))
):
    nota = db.query(Nota).filter(Nota.id_nota == id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    if data.nota is not None and (float(data.nota) < 0 or float(data.nota) > 100):
        raise HTTPException(status_code=400, detail="La nota debe estar entre 0 y 100")

    detalle_nota = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == nota.id_detalle_programa_alumno
    ).first()
    if detalle_nota and _es_alumno_actual(current_user, detalle_nota.id_alumno, db):
        raise HTTPException(status_code=403, detail="No podés calificar tu propia inscripción")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(nota, key, value)
    db.flush()
    db.refresh(nota)
    return nota


@router.delete("/{id}", status_code=204)
def eliminar_nota(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("notas.subir"))
):
    nota = db.query(Nota).filter(Nota.id_nota == id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    detalle_nota = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == nota.id_detalle_programa_alumno
    ).first()
    if detalle_nota and _es_alumno_actual(current_user, detalle_nota.id_alumno, db):
        raise HTTPException(status_code=403, detail="No podés eliminar notas de tu propia inscripción")

    db.delete(nota)
    db.flush()
