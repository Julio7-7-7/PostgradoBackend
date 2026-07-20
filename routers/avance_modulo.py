from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from database import get_db
from dependencies import get_current_user, require_permiso
from models.avance_modulo import AvanceModulo
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.modulo import Modulo
from models.nota import Nota
from models.programa_version_edicion import ProgramaVersionEdicion
from models.programa_version import ProgramaVersion
from models.programa import Programa
from models.alumno import Alumno
from models.modalidad_academica import ModalidadAcademica
from schemas.avance_modulo import (
    AvanceModuloCreate,
    AvanceModuloResponse,
    ModuloTranscriptItem,
    InscripcionTranscriptItem,
    TranscriptResponse,
)
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/avance-modulo",
    tags=["Avance de Módulo"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=AvanceModuloResponse, status_code=201)
def registrar_avance(
    data: AvanceModuloCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("notas.subir")),
):
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

    existente = db.query(AvanceModulo).filter(
        AvanceModulo.id_detalle_programa_alumno == data.id_detalle_programa_alumno,
        AvanceModulo.id_detalle_programa_modulo == data.id_detalle_programa_modulo,
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un registro de avance para este módulo")

    nuevo = AvanceModulo(**data.model_dump())
    db.add(nuevo)
    db.flush()
    db.refresh(nuevo)
    return nuevo


@router.get("/por-inscripcion/{id_detalle}", response_model=list[AvanceModuloResponse])
def avance_por_inscripcion(
    id_detalle: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("alumnos.ver")),
):
    return db.query(AvanceModulo).filter(
        AvanceModulo.id_detalle_programa_alumno == id_detalle
    ).all()


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
        DetalleProgramaAlumno.id_alumno == id_alumno
    ).order_by(DetalleProgramaAlumno.id_detalle_programa_alumno).all()

    if not inscripciones:
        return TranscriptResponse(
            id_alumno=id_alumno,
            alumno_nombre=alumno.nombre,
            alumno_apellido=alumno.apellido,
            alumno_ci=alumno.ci,
            inscripciones=[],
            promedio_general=None,
        )

    inscripcion_ids = [i.id_detalle_programa_alumno for i in inscripciones]

    avances = db.query(AvanceModulo).filter(
        AvanceModulo.id_detalle_programa_alumno.in_(inscripcion_ids)
    ).all()

    avance_map: dict[int, list[AvanceModulo]] = {}
    for a in avances:
        avance_map.setdefault(a.id_detalle_programa_alumno, []).append(a)

    notas = db.query(Nota).filter(
        Nota.id_detalle_programa_alumno.in_(inscripcion_ids)
    ).all()

    nota_map: dict[int, list[Nota]] = {}
    for n in notas:
        nota_map.setdefault(n.id_detalle_programa_alumno, []).append(n)

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
        avances_ins = avance_map.get(ins.id_detalle_programa_alumno, [])
        for a in avances_ins:
            all_dpm_ids.add(a.id_detalle_programa_modulo)
    for ins in inscripciones:
        for n in nota_map.get(ins.id_detalle_programa_alumno, []):
            all_dpm_ids.add(n.id_detalle_programa_modulo)

    dpm_list = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo.in_(all_dpm_ids)
    ).all() if all_dpm_ids else []

    dpm_map = {dpm.id_detalle_programa_modulo: dpm for dpm in dpm_list}

    modulo_ids = {dpm.id_modulo for dpm in dpm_list}
    modulos = db.query(Modulo).filter(
        Modulo.id_modulo.in_(modulo_ids)
    ).all() if modulo_ids else []
    modulo_info_map = {m.id_modulo: m for m in modulos}

    inscripciones_items: list[InscripcionTranscriptItem] = []
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

        avances_ins = avance_map.get(ins.id_detalle_programa_alumno, [])
        modulos_items: list[ModuloTranscriptItem] = []
        notas_finales: list[float] = []

        for av in avances_ins:
            dpm = dpm_map.get(av.id_detalle_programa_modulo)
            if not dpm:
                continue
            mod = modulo_info_map.get(dpm.id_modulo)
            nota_obj = nota_by_dpm.get(av.id_detalle_programa_modulo)
            nota_val = float(nota_obj.nota) if nota_obj else None
            nota_tipo = nota_obj.tipo if nota_obj else None
            edicion_av = pve_map.get(av.completado_en_edicion)

            modulos_items.append(ModuloTranscriptItem(
                id_detalle_programa_modulo=av.id_detalle_programa_modulo,
                modulo_nombre=mod.nombre_modulo if mod else f"Módulo #{dpm.id_modulo}",
                modulo_orden=dpm.orden,
                nota=nota_val,
                nota_tipo=nota_tipo,
                completado_en_edicion=av.completado_en_edicion,
                edicion_numero=edicion_av.edicion if edicion_av else None,
                edicion_anio=edicion_av.anio if edicion_av else None,
                edicion_semestre=edicion_av.semestre if edicion_av else None,
                fecha_completion=av.fecha_completion,
            ))

            if nota_val is not None and nota_tipo == "final":
                notas_finales.append(nota_val)

        promedio_ins = round(sum(notas_finales) / len(notas_finales), 2) if notas_finales else None
        todas_notas.extend(notas_finales)

        inscripciones_items.append(InscripcionTranscriptItem(
            id_detalle_programa_alumno=ins.id_detalle_programa_alumno,
            estado=ins.estado,
            edicion_id=ins.id_programa_version_edicion,
            edicion_numero=pve.edicion if pve else None,
            edicion_anio=pve.anio if pve else None,
            edicion_semestre=pve.semestre if pve else None,
            programa_nombre=prog.nombre_programa if prog else "N/A",
            modalidad_nombre=modalidad.nombre_modalidad if modalidad else "N/A",
            modulos=modulos_items,
            promedio=promedio_ins,
        ))

    promedio_general = round(sum(todas_notas) / len(todas_notas), 2) if todas_notas else None

    return TranscriptResponse(
        id_alumno=id_alumno,
        alumno_nombre=alumno.nombre,
        alumno_apellido=alumno.apellido,
        alumno_ci=alumno.ci,
        inscripciones=inscripciones_items,
        promedio_general=promedio_general,
    )
