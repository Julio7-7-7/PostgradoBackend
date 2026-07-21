from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from dependencies import get_current_user, require_permiso
from models.nota import Nota
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.alumno import Alumno
from models.modulo import Modulo
from models.contratacion_docente import ContratacionDocente
from models.programa_version_edicion import ProgramaVersionEdicion
from models.programa_version import ProgramaVersion
from schemas.nota import NotaCreate, NotaUpdate, NotaResponse
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/notas",
    tags=["Notas"],
    dependencies=[Depends(get_current_user)]
)

ESTADOS_NOTAS_PERMITIDOS = {"inscrito", "incorporado", "finalizado", "graduado"}


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

    dpa_ids = [d.id_detalle_programa_alumno for d in detalles_alumno]
    alumno_ids = {d.id_alumno for d in detalles_alumno}

    detalles_modulo = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == id_edicion
    ).all()

    modulo_ids = {dm.id_modulo for dm in detalles_modulo}
    modulos_db = db.query(Modulo).filter(Modulo.id_modulo.in_(modulo_ids)).all() if modulo_ids else []
    modulo_info_map = {m.id_modulo: m for m in modulos_db}

    modulos_map = {}
    for dm in detalles_modulo:
        mod = modulo_info_map.get(dm.id_modulo)
        modulos_map[dm.id_detalle_programa_modulo] = {
            "id_detalle_programa_modulo": dm.id_detalle_programa_modulo,
            "nombre": mod.nombre_modulo if mod else f"Módulo #{dm.id_modulo}",
            "orden": dm.orden,
        }

    alumnos_db = db.query(Alumno).filter(Alumno.id_alumno.in_(alumno_ids)).all() if alumno_ids else []
    alumno_map = {a.id_alumno: a for a in alumnos_db}

    notas_db = db.query(Nota).filter(
        Nota.id_detalle_programa_alumno.in_(dpa_ids)
    ).all() if dpa_ids else []

    notas_por_dpa: dict[int, list[Nota]] = {}
    for n in notas_db:
        notas_por_dpa.setdefault(n.id_detalle_programa_alumno, []).append(n)

    resultado = []
    for detalle in detalles_alumno:
        alumno = alumno_map.get(detalle.id_alumno)
        notas = notas_por_dpa.get(detalle.id_detalle_programa_alumno, [])

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

    if detalle.estado not in ESTADOS_NOTAS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"No se pueden registrar notas para una inscripción con estado '{detalle.estado}'"
        )

    if _es_alumno_actual(current_user, detalle.id_alumno, db):
        raise HTTPException(status_code=403, detail="No podés calificar tu propia inscripción")

    dm = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == data.id_detalle_programa_modulo
    ).first()
    if not dm:
        raise HTTPException(status_code=404, detail="Módulo no encontrado")

    if dm.id_programa_version_edicion != detalle.id_programa_version_edicion:
        raise HTTPException(
            status_code=400,
            detail="El módulo no pertenece a la edición de esta inscripción"
        )

    if float(data.nota) < 0 or float(data.nota) > 100:
        raise HTTPException(status_code=400, detail="La nota debe estar entre 0 y 100")

    nota_data = data.model_dump()
    nota_data["id_programa_version_edicion"] = detalle.id_programa_version_edicion

    nuevo = Nota(**nota_data)
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


def _resolver_docente(usuario: UserResponse, db: Session) -> int:
    if usuario.profile_type == "docente" and usuario.id_profile:
        return usuario.id_profile
    from models.docente import Docente
    docente = db.query(Docente).filter(Docente.id_usuario == usuario.id_usuario).first()
    if not docente:
        raise HTTPException(status_code=404, detail="No se encontró un docente asociado a este usuario")
    return docente.id_docente


@router.get("/por-docente/{id_docente}")
def notas_por_docente(
    id_docente: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("notas.ver"))
):
    modulos_asignados = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_docente == id_docente,
        ContratacionDocente.estado != "truncado",
    ).all()

    if not modulos_asignados:
        return []

    dpm_ids = [c.id_detalle_modulo for c in modulos_asignados]

    detalles_modulo = db.query(DetalleProgramaModulo).options(
        joinedload(DetalleProgramaModulo.modulo),
        joinedload(DetalleProgramaModulo.programa_version_edicion)
            .joinedload(ProgramaVersionEdicion.programa_version)
            .joinedload(ProgramaVersion.programa),
    ).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo.in_(dpm_ids)
    ).all()

    edicion_ids = list({dm.id_programa_version_edicion for dm in detalles_modulo})
    alumnos_en_ediciones = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_programa_version_edicion.in_(edicion_ids),
        DetalleProgramaAlumno.estado.notin_(["postulante", "observado", "retirado"]),
    ).all() if edicion_ids else []

    dpa_ids = [d.id_detalle_programa_alumno for d in alumnos_en_ediciones]
    alumno_ids = list({d.id_alumno for d in alumnos_en_ediciones})
    alumnos_db = db.query(Alumno).filter(Alumno.id_alumno.in_(alumno_ids)).all() if alumno_ids else []
    alumno_map = {a.id_alumno: a for a in alumnos_db}

    notas_db = db.query(Nota).filter(Nota.id_detalle_programa_alumno.in_(dpa_ids)).all() if dpa_ids else []
    notas_por_dpa: dict[int, list[Nota]] = {}
    for n in notas_db:
        notas_por_dpa.setdefault(n.id_detalle_programa_alumno, []).append(n)

    edicion_info_map = {}
    for dm in detalles_modulo:
        pve = dm.programa_version_edicion
        pv = pve.programa_version if pve else None
        prog = pv.programa if pv else None
        edicion_info_map[dm.id_programa_version_edicion] = {
            "id_programa_version_edicion": dm.id_programa_version_edicion,
            "edicion_numero": pve.edicion if pve else 0,
            "anio": pve.anio if pve else 0,
            "semestre": pve.semestre if pve else 0,
            "programa_nombre": prog.nombre_programa if prog else "N/A",
            "estado": pve.estado if pve else "N/A",
        }

    modulos_map = {}
    for dm in detalles_modulo:
        mod = dm.modulo
        modulos_map[dm.id_detalle_programa_modulo] = {
            "id_detalle_programa_modulo": dm.id_detalle_programa_modulo,
            "nombre": mod.nombre_modulo if mod else f"Módulo #{dm.id_modulo}",
            "sigla": mod.sigla if mod else "",
            "orden": dm.orden,
            "estado": dm.estado,
            "fecha_inicio": str(dm.fecha_inicio) if dm.fecha_inicio else None,
            "fecha_fin": str(dm.fecha_fin) if dm.fecha_fin else None,
            "num_alumnos": 0,
        }

    dpa_por_edicion: dict[int, list] = {}
    for d in alumnos_en_ediciones:
        dpa_por_edicion.setdefault(d.id_programa_version_edicion, []).append(d)

    resultado = []
    for ed_id, ed_info in edicion_info_map.items():
        dpa_list = dpa_por_edicion.get(ed_id, [])
        alumnos_data = []
        for dpa in dpa_list:
            alumno = alumno_map.get(dpa.id_alumno)
            notas = notas_por_dpa.get(dpa.id_detalle_programa_alumno, [])
            alumnos_data.append({
                "id_detalle_programa_alumno": dpa.id_detalle_programa_alumno,
                "alumno": {
                    "id_alumno": alumno.id_alumno if alumno else None,
                    "nombre": alumno.nombre if alumno else "N/A",
                    "apellido": alumno.apellido if alumno else "N/A",
                    "ci": alumno.ci if alumno else None,
                } if alumno else None,
                "modulo_inicio": dpa.modulo_inicio,
                "estado": dpa.estado,
                "notas_count": len(notas),
            })

        modulos_edicion = [m for m in modulos_map.values()
                          if any(dm.id_programa_version_edicion == ed_id
                                 for dm in detalles_modulo
                                 if dm.id_detalle_programa_modulo == m["id_detalle_programa_modulo"])]
        for m in modulos_edicion:
            m["num_alumnos"] = len(dpa_list)

        resultado.append({
            "edicion": ed_info,
            "modulos": modulos_edicion,
            "alumnos": alumnos_data,
        })

    return resultado


@router.get("/por-modulo/{id_dpm}")
def notas_por_modulo(
    id_dpm: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("notas.ver"))
):
    dm = db.query(DetalleProgramaModulo).options(
        joinedload(DetalleProgramaModulo.modulo),
        joinedload(DetalleProgramaModulo.programa_version_edicion)
            .joinedload(ProgramaVersionEdicion.programa_version)
            .joinedload(ProgramaVersion.programa),
    ).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == id_dpm
    ).first()
    if not dm:
        raise HTTPException(status_code=404, detail="Módulo no encontrado")

    pve = dm.programa_version_edicion
    pv = pve.programa_version if pve else None
    prog = pv.programa if pv else None

    alumnos_en_edicion = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_programa_version_edicion == dm.id_programa_version_edicion,
        DetalleProgramaAlumno.estado.notin_(["postulante", "observado", "retirado"]),
    ).all()

    dpa_ids = [d.id_detalle_programa_alumno for d in alumnos_en_edicion]
    alumno_ids = list({d.id_alumno for d in alumnos_en_edicion})
    alumnos_db = db.query(Alumno).filter(Alumno.id_alumno.in_(alumno_ids)).all() if alumno_ids else []
    alumno_map = {a.id_alumno: a for a in alumnos_db}

    notas_db = db.query(Nota).filter(
        Nota.id_detalle_programa_modulo == id_dpm,
        Nota.id_detalle_programa_alumno.in_(dpa_ids),
    ).all() if dpa_ids else []
    notas_por_dpa: dict[int, list[Nota]] = {}
    for n in notas_db:
        notas_por_dpa.setdefault(n.id_detalle_programa_alumno, []).append(n)

    mod = dm.modulo
    resultado = {
        "modulo": {
            "id_detalle_programa_modulo": dm.id_detalle_programa_modulo,
            "nombre": mod.nombre_modulo if mod else "N/A",
            "sigla": mod.sigla if mod else "",
            "orden": dm.orden,
            "estado": dm.estado,
            "fecha_inicio": str(dm.fecha_inicio) if dm.fecha_inicio else None,
            "fecha_fin": str(dm.fecha_fin) if dm.fecha_fin else None,
        },
        "edicion": {
            "id_programa_version_edicion": dm.id_programa_version_edicion,
            "edicion_numero": pve.edicion if pve else 0,
            "anio": pve.anio if pve else 0,
            "semestre": pve.semestre if pve else 0,
            "programa_nombre": prog.nombre_programa if prog else "N/A",
        },
        "alumnos": [],
    }

    for dpa in alumnos_en_edicion:
        alumno = alumno_map.get(dpa.id_alumno)
        notas = notas_por_dpa.get(dpa.id_detalle_programa_alumno, [])
        notas_data = []
        for n in notas:
            notas_data.append({
                "id_nota": n.id_nota,
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

        resultado["alumnos"].append({
            "id_detalle_programa_alumno": dpa.id_detalle_programa_alumno,
            "alumno": {
                "id_alumno": alumno.id_alumno if alumno else None,
                "nombre": alumno.nombre if alumno else "N/A",
                "apellido": alumno.apellido if alumno else "N/A",
                "ci": alumno.ci if alumno else None,
            } if alumno else None,
            "modulo_inicio": dpa.modulo_inicio,
            "estado": dpa.estado,
            "notas": notas_data,
            "promedio": promedio,
        })

    return resultado
