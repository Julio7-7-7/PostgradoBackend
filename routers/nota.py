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
from models.programa import Programa
from models.modalidad_academica import ModalidadAcademica
from models.historial_inscripcion import HistorialInscripcion
from schemas.nota import (
    NotaCreate, NotaUpdate, NotaResponse,
    NotaEdicionResponse, NotaDocenteResponse, NotaModuloResponse,
    ModuloTranscriptItem, InscripcionTranscriptItem, EdicionInfoItem, TranscriptResponse,
)
from schemas.enums import clasificar_nota, redondear_nota, ESTADOS_CON_CALIFICACION
from schemas.auth import UserResponse
from routers.utils import es_alumno_actual

router = APIRouter(
    prefix="/notas",
    tags=["Notas"],
    dependencies=[Depends(get_current_user)]
)


def _es_docente(user: UserResponse) -> bool:
    return user.profile_type == "docente"


def _tiene_contratacion(db: Session, id_dpm: int, id_docente: int) -> bool:
    return db.query(ContratacionDocente).filter(
        ContratacionDocente.id_detalle_modulo == id_dpm,
        ContratacionDocente.id_docente == id_docente,
        ContratacionDocente.estado != "truncado",
    ).first() is not None


def _es_modulo_en_curso(db: Session, id_dpm: int) -> bool:
    dm = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == id_dpm
    ).first()
    return dm is not None and dm.estado == "en_curso"


@router.get("/por-edicion/{id_edicion}", response_model=list[NotaEdicionResponse])
def notas_por_edicion(
    id_edicion: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("notas.ver"))
):
    if _es_docente(current_user):
        raise HTTPException(
            status_code=403,
            detail="El docente solo puede consultar notas de sus módulos asignados",
        )

    estados_permitidos = ESTADOS_CON_CALIFICACION | {"retirado"}
    detalles_alumno = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_programa_version_edicion == id_edicion,
        DetalleProgramaAlumno.estado.in_(estados_permitidos),
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
                "calificacion": clasificar_nota(float(n.nota)),
                "fecha": n.fecha,
                "created_at": n.created_at,
                "updated_at": n.updated_at,
            })

        promedio = 0
        if notas_data:
            promedio = redondear_nota(sum(n["nota"] for n in notas_data) / len(notas_data))

        resultado.append({
            "id_detalle_programa_alumno": detalle.id_detalle_programa_alumno,
            "alumno": {
                "id_alumno": alumno.id_alumno if alumno else None,
                "nombre": alumno.nombre if alumno else "N/A",
                "apellido": alumno.apellido if alumno else "N/A",
                "ci": alumno.ci if alumno else None,
            } if alumno else None,
            "modulo_inicio": detalle.modulo_inicio,
            "estado": detalle.estado,
            "notas": notas_data,
            "promedio": promedio,
        })

    return resultado


@router.post("/", response_model=NotaResponse, status_code=201)
def crear_nota(data: NotaCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("notas.subir"))):
    if not _es_docente(current_user) or not current_user.id_profile:
        raise HTTPException(status_code=403, detail="Solo el docente responsable puede cargar notas")

    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == data.id_detalle_programa_alumno
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    if detalle.estado not in ESTADOS_CON_CALIFICACION:
        raise HTTPException(
            status_code=400,
            detail=f"No se pueden registrar notas para una inscripción con estado '{detalle.estado}'"
        )

    if es_alumno_actual(current_user, detalle.id_alumno, db):
        raise HTTPException(status_code=403, detail="No podés calificar tu propia inscripción")

    dm = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == data.id_detalle_programa_modulo
    ).first()
    if not dm:
        raise HTTPException(status_code=404, detail="Módulo no encontrado")

    if not _tiene_contratacion(db, dm.id_detalle_programa_modulo, current_user.id_profile):
        raise HTTPException(
            status_code=403,
            detail="El módulo no está asignado a este docente",
        )

    if dm.estado != "en_curso":
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden registrar notas de un módulo en curso",
        )

    if dm.id_programa_version_edicion != detalle.id_programa_version_edicion:
        raise HTTPException(
            status_code=400,
            detail="El módulo no pertenece a la edición de esta inscripción"
        )

    if float(data.nota) < 0 or float(data.nota) > 100:
        raise HTTPException(status_code=400, detail="La nota debe estar entre 0 y 100")

    existente = db.query(Nota).filter(
        Nota.id_detalle_programa_alumno == data.id_detalle_programa_alumno,
        Nota.id_detalle_programa_modulo == data.id_detalle_programa_modulo,
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una nota para este alumno en este módulo. Use editar para modificarla.")

    nota_data = data.model_dump()

    nuevo = Nota(**nota_data)
    db.add(nuevo)
    db.flush()
    db.refresh(nuevo)
    db.commit()
    return nuevo


@router.patch("/{id}", response_model=NotaResponse)
def editar_nota(
    id: int,
    data: NotaUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("notas.subir"))
):
    if not _es_docente(current_user) or not current_user.id_profile:
        raise HTTPException(status_code=403, detail="Solo el docente responsable puede editar notas")

    nota = db.query(Nota).filter(Nota.id_nota == id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    if not _tiene_contratacion(db, nota.id_detalle_programa_modulo, current_user.id_profile):
        raise HTTPException(
            status_code=403,
            detail="El módulo no está asignado a este docente",
        )

    if not _es_modulo_en_curso(db, nota.id_detalle_programa_modulo):
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden editar notas de un módulo en curso",
        )

    if data.nota is not None and (float(data.nota) < 0 or float(data.nota) > 100):
        raise HTTPException(status_code=400, detail="La nota debe estar entre 0 y 100")

    detalle_nota = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == nota.id_detalle_programa_alumno
    ).first()
    if detalle_nota and es_alumno_actual(current_user, detalle_nota.id_alumno, db):
        raise HTTPException(status_code=403, detail="No podés calificar tu propia inscripción")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(nota, key, value)
    db.flush()
    db.refresh(nota)
    db.commit()
    return nota


@router.get("/por-docente/{id_docente}", response_model=list[NotaDocenteResponse])
def notas_por_docente(
    id_docente: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("notas.ver"))
):
    if _es_docente(current_user) and current_user.id_profile:
        id_docente = current_user.id_profile

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
        DetalleProgramaAlumno.estado.in_(ESTADOS_CON_CALIFICACION),
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
            "fecha_inicio": dm.fecha_inicio,
            "fecha_fin": dm.fecha_fin,
            "num_alumnos": 0,
        }

    dpa_por_edicion: dict[int, list] = {}
    for d in alumnos_en_ediciones:
        dpa_por_edicion.setdefault(d.id_programa_version_edicion, []).append(d)

    dpa_por_modulo: dict[int, set[int]] = {}
    for n in notas_db:
        dpa_por_modulo.setdefault(n.id_detalle_programa_modulo, set()).add(n.id_detalle_programa_alumno)

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
            m["num_alumnos"] = len(dpa_por_modulo.get(m["id_detalle_programa_modulo"], set()))

        resultado.append({
            "edicion": ed_info,
            "modulos": modulos_edicion,
            "alumnos": alumnos_data,
        })

    return resultado


@router.get("/por-modulo/{id_dpm}", response_model=NotaModuloResponse)
def notas_por_modulo(
    id_dpm: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("notas.ver"))
):
    if _es_docente(current_user):
        if not current_user.id_profile or not _tiene_contratacion(db, id_dpm, current_user.id_profile):
            raise HTTPException(
                status_code=403,
                detail="El módulo no está asignado a este docente",
            )

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
        DetalleProgramaAlumno.estado.in_(ESTADOS_CON_CALIFICACION),
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
            "fecha_inicio": dm.fecha_inicio,
            "fecha_fin": dm.fecha_fin,
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
                "calificacion": clasificar_nota(float(n.nota)),
                "fecha": n.fecha,
                "created_at": n.created_at,
                "updated_at": n.updated_at,
            })
        promedio = 0
        if notas_data:
            promedio = redondear_nota(sum(n["nota"] for n in notas_data) / len(notas_data))

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


@router.get("/transcript/{id_alumno}", response_model=TranscriptResponse)
def transcript_alumno(
    id_alumno: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.ver")),
):
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id_alumno).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    inscripciones = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_alumno == id_alumno,
        DetalleProgramaAlumno.estado != "retirado",
    ).order_by(
        ProgramaVersionEdicion.edicion,
        ProgramaVersionEdicion.anio,
        ProgramaVersionEdicion.semestre,
    ).join(
        ProgramaVersionEdicion,
        ProgramaVersionEdicion.id_programa_version_edicion == DetalleProgramaAlumno.id_programa_version_edicion,
    ).all()

    if not inscripciones:
        return TranscriptResponse(
            id_alumno=id_alumno,
            alumno_nombre=alumno.nombre,
            alumno_apellido=alumno.apellido,
            alumno_ci=alumno.ci,
            inscripciones=[],
            ediciones_info=[],
            promedio_general=None,
        )

    inscripcion_ids = [i.id_detalle_programa_alumno for i in inscripciones]

    notas = db.query(Nota).filter(
        Nota.id_detalle_programa_alumno.in_(inscripcion_ids)
    ).all() if inscripcion_ids else []

    historiales = db.query(HistorialInscripcion).filter(
        (HistorialInscripcion.id_detalle_destino.in_(inscripcion_ids))
    ).all() if inscripcion_ids else []
    historial_by_destino = {h.id_detalle_destino: h for h in historiales}
    historial_by_origen = {h.id_detalle_origen: h for h in historiales}

    origen_ids = {h.id_detalle_origen for h in historiales}
    destino_ids = {h.id_detalle_destino for h in historiales}
    origen_dpas_list = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno.in_(origen_ids)
    ).all() if origen_ids else []
    origen_dpa_map = {d.id_detalle_programa_alumno: d for d in origen_dpas_list}

    destino_dpas_list = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno.in_(destino_ids)
    ).all() if destino_ids else []
    destino_dpa_map = {d.id_detalle_programa_alumno: d for d in destino_dpas_list}

    notas_origen = db.query(Nota).filter(
        Nota.id_detalle_programa_alumno.in_(origen_ids)
    ).all() if origen_ids else []

    nota_map: dict[int, list[Nota]] = {}
    for n in notas:
        nota_map.setdefault(n.id_detalle_programa_alumno, []).append(n)

    nota_origen_map: dict[int, list[Nota]] = {}
    for n in notas_origen:
        nota_origen_map.setdefault(n.id_detalle_programa_alumno, []).append(n)

    all_origen_dpm_ids = {n.id_detalle_programa_modulo for n in notas_origen}
    origen_dpms = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo.in_(all_origen_dpm_ids)
    ).all() if all_origen_dpm_ids else []
    origen_dpm_map = {dpm.id_detalle_programa_modulo: dpm for dpm in origen_dpms}

    pve_ids = {i.id_programa_version_edicion for i in inscripciones}
    pves = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion.in_(pve_ids)
    ).all() if pve_ids else []

    pv_ids = {pve.id_programa_version for pve in pves}
    pvs = db.query(ProgramaVersion).filter(
        ProgramaVersion.id_programa_version.in_(pv_ids)
    ).all() if pv_ids else []

    prog_ids = {pv.id_programa for pv in pvs}
    progs = db.query(Programa).filter(
        Programa.id_programa.in_(prog_ids)
    ).all() if prog_ids else []

    pve_map = {pve.id_programa_version_edicion: pve for pve in pves}
    pv_map = {pv.id_programa_version: pv for pv in pvs}
    prog_map = {p.id_programa: p for p in progs}

    modalidad_ids = {i.id_modalidad_academica for i in inscripciones}
    modalidades = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.id_modalidad_academica.in_(modalidad_ids)
    ).all() if modalidad_ids else []
    mod_map = {m.id_modalidad_academica: m for m in modalidades}

    all_dpm_ids = set()
    for ins in inscripciones:
        for n in nota_map.get(ins.id_detalle_programa_alumno, []):
            all_dpm_ids.add(n.id_detalle_programa_modulo)

    dpm_list = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo.in_(all_dpm_ids)
    ).all() if all_dpm_ids else []

    dpm_map = {dpm.id_detalle_programa_modulo: dpm for dpm in dpm_list}

    todos_dpm = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion.in_(pve_ids)
    ).order_by(DetalleProgramaModulo.orden).all() if pve_ids else []
    dpm_por_edicion: dict[int, list[DetalleProgramaModulo]] = {}
    for dpm in todos_dpm:
        dpm_por_edicion.setdefault(dpm.id_programa_version_edicion, []).append(dpm)

    dpm_by_id = {dpm.id_detalle_programa_modulo: dpm for dpm in todos_dpm}

    all_modulo_ids = {dpm.id_modulo for dpm in todos_dpm}
    modulos = db.query(Modulo).filter(
        Modulo.id_modulo.in_(all_modulo_ids)
    ).all() if all_modulo_ids else []
    modulo_info_map = {m.id_modulo: m for m in modulos}

    inscripcion_items: list[InscripcionTranscriptItem] = []
    todas_notas: list[float] = []

    for ins in inscripciones:
        pve = pve_map.get(ins.id_programa_version_edicion)
        pv = pv_map.get(pve.id_programa_version) if pve else None
        prog = prog_map.get(pv.id_programa) if pv else None
        modalidad = mod_map.get(ins.id_modalidad_academica)

        notas_ins = nota_map.get(ins.id_detalle_programa_alumno, [])
        nota_by_dpm: dict[int, Nota] = {}
        for n in notas_ins:
            existing = nota_by_dpm.get(n.id_detalle_programa_modulo)
            if not existing or n.id_nota > existing.id_nota:
                nota_by_dpm[n.id_detalle_programa_modulo] = n

        historial = historial_by_destino.get(ins.id_detalle_programa_alumno)
        historial_origen = historial_by_origen.get(ins.id_detalle_programa_alumno)

        migrado_a_edicion_numero = None
        migrado_a_edicion_anio = None
        migrado_a_edicion_semestre = None
        if historial_origen:
            dpa_dest = destino_dpa_map.get(historial_origen.id_detalle_destino)
            if dpa_dest:
                pve_dest = pve_map.get(dpa_dest.id_programa_version_edicion)
                if not pve_dest:
                    pve_dest_obj = db.query(ProgramaVersionEdicion).get(dpa_dest.id_programa_version_edicion)
                    pve_dest = pve_dest_obj
                if pve_dest:
                    migrado_a_edicion_numero = pve_dest.edicion
                    migrado_a_edicion_anio = pve_dest.anio
                    migrado_a_edicion_semestre = pve_dest.semestre

        origen_nota_by_id_modulo: dict[int, float] = {}
        if historial:
            notas_o = nota_origen_map.get(historial.id_detalle_origen, [])
            nota_o_by_dpm: dict[int, Nota] = {}
            for n in notas_o:
                existing = nota_o_by_dpm.get(n.id_detalle_programa_modulo)
                if not existing or n.id_nota > existing.id_nota:
                    nota_o_by_dpm[n.id_detalle_programa_modulo] = n
            for dpm_o_id, n_o in nota_o_by_dpm.items():
                dpm_o = origen_dpm_map.get(dpm_o_id)
                if dpm_o:
                    origen_nota_by_id_modulo[dpm_o.id_modulo] = float(n_o.nota)

        todos_los_dpm = dpm_por_edicion.get(ins.id_programa_version_edicion, [])

        modulos_items: list[ModuloTranscriptItem] = []
        notas_finales: list[float] = []

        for dpm in todos_los_dpm:
            mod = modulo_info_map.get(dpm.id_modulo)
            nota_obj = nota_by_dpm.get(dpm.id_detalle_programa_modulo)
            nota_val = float(nota_obj.nota) if nota_obj else None

            pve_dpm = pve_map.get(dpm.id_programa_version_edicion)

            es_migrada = False
            edicion_origen_numero = None
            edicion_origen_anio = None
            edicion_origen_semestre = None

            if nota_val is None and historial:
                if dpm.id_modulo in origen_nota_by_id_modulo:
                    nota_val = origen_nota_by_id_modulo[dpm.id_modulo]
                    es_migrada = True
                    dpa_origen = origen_dpa_map.get(historial.id_detalle_origen) if historial else None
                    pve_origen_h = pve_map.get(dpa_origen.id_programa_version_edicion) if dpa_origen else None
                    edicion_origen_numero = pve_origen_h.edicion if pve_origen_h else None
                    edicion_origen_anio = pve_origen_h.anio if pve_origen_h else None
                    edicion_origen_semestre = pve_origen_h.semestre if pve_origen_h else None

            modulos_items.append(ModuloTranscriptItem(
                id_detalle_programa_modulo=dpm.id_detalle_programa_modulo,
                modulo_nombre=mod.nombre_modulo if mod else f"Módulo #{dpm.id_modulo}",
                modulo_orden=dpm.orden,
                nota=nota_val,
                calificacion=clasificar_nota(nota_val) if nota_val is not None else None,
                edicion_numero=pve_dpm.edicion if pve_dpm else None,
                edicion_anio=pve_dpm.anio if pve_dpm else None,
                edicion_semestre=pve_dpm.semestre if pve_dpm else None,
                es_migrada=es_migrada,
                edicion_origen_numero=edicion_origen_numero,
                edicion_origen_anio=edicion_origen_anio,
                edicion_origen_semestre=edicion_origen_semestre,
                migrado_a_edicion_numero=migrado_a_edicion_numero,
                migrado_a_edicion_anio=migrado_a_edicion_anio,
                migrado_a_edicion_semestre=migrado_a_edicion_semestre,
            ))

            if nota_val is not None:
                notas_finales.append(nota_val)

        promedio_ins = redondear_nota(sum(notas_finales) / len(notas_finales)) if notas_finales else None
        todas_notas.extend(notas_finales)

        mod_inicio_efectivo = ins.modulo_inicio or 1
        if ins.id_modulo_inicio:
            dpm_inicio = dpm_by_id.get(ins.id_modulo_inicio)
            if dpm_inicio:
                mod_inicio_efectivo = dpm_inicio.orden

        inscripcion_items.append(InscripcionTranscriptItem(
            id_detalle_programa_alumno=ins.id_detalle_programa_alumno,
            estado=ins.estado,
            edicion_id=ins.id_programa_version_edicion,
            edicion_numero=pve.edicion if pve else None,
            edicion_anio=pve.anio if pve else None,
            edicion_semestre=pve.semestre if pve else None,
            programa_nombre=prog.nombre_programa if prog else "N/A",
            modalidad_nombre=modalidad.nombre_modalidad if modalidad else "N/A",
            modulo_inicio=mod_inicio_efectivo,
            modulos=modulos_items,
            promedio=promedio_ins,
            migrado_a_edicion_numero=migrado_a_edicion_numero,
            migrado_a_edicion_anio=migrado_a_edicion_anio,
            migrado_a_edicion_semestre=migrado_a_edicion_semestre,
        ))

    promedio_general = redondear_nota(sum(todas_notas) / len(todas_notas)) if todas_notas else None

    ediciones_info = []
    for pve in pves:
        pv = pv_map.get(pve.id_programa_version)
        prog = prog_map.get(pv.id_programa) if pv else None
        ediciones_info.append(EdicionInfoItem(
            id_programa_version_edicion=pve.id_programa_version_edicion,
            edicion_numero=pve.edicion,
            anio=pve.anio,
            semestre=pve.semestre,
            programa_nombre=prog.nombre_programa if prog else "N/A",
            estado=pve.estado,
        ))

    return TranscriptResponse(
        id_alumno=id_alumno,
        alumno_nombre=alumno.nombre,
        alumno_apellido=alumno.apellido,
        alumno_ci=alumno.ci,
        inscripciones=inscripcion_items,
        ediciones_info=ediciones_info,
        promedio_general=promedio_general,
    )
