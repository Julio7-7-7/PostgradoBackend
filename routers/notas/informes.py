from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_permiso
from models.informe_notas import InformeNotas
from models.certificado_notas import CertificadoNotas
from schemas.auth import UserResponse
from schemas.informe_notas import InformeNotasRequest
from routers.notas._builder_informes import (
    armar_contenido, resolver_edicion, calcular_elegibilidad,
)

router = APIRouter(
    prefix="/informes-notas",
    tags=["Informes de Notas"],
    dependencies=[Depends(get_current_user)],
)


def _serializar_informe(informe: InformeNotas, cert_count: int = 0) -> dict:
    return {
        "id_informe": informe.id_informe,
        "id_programa_version_edicion": informe.id_programa_version_edicion,
        "numero_tanda": informe.numero_tanda,
        "tipo": informe.tipo,
        "fecha_emision": str(informe.fecha_emision),
        "generado_at": informe.generado_at.isoformat() if informe.generado_at else None,
        "estado": informe.estado,
        "observaciones": informe.observaciones,
        "contenido": informe.contenido,
        "certificados_count": cert_count,
        "created_at": informe.created_at.isoformat() if informe.created_at else None,
        "updated_at": informe.updated_at.isoformat() if informe.updated_at else None,
    }


def _siguiente_tanda(db: Session, id_edicion: int) -> int:
    ultimo = db.query(InformeNotas).filter(
        InformeNotas.id_programa_version_edicion == id_edicion
    ).order_by(InformeNotas.numero_tanda.desc()).first()
    return (ultimo.numero_tanda + 1) if ultimo else 1


def _certificados_por_informe(db: Session, id_informe: int) -> int:
    return db.query(CertificadoNotas).filter(
        CertificadoNotas.id_informe == id_informe
    ).count()


@router.post("/preview")
def preview_informe(
    data: InformeNotasRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver")),
):
    contenido = armar_contenido(db, data)
    pve, _, _ = resolver_edicion(db, data.id_programa_version_edicion)
    return {
        **contenido,
        "numero_tanda": _siguiente_tanda(db, data.id_programa_version_edicion),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "es_borrador": True,
        "edicion_estado": pve.estado,
    }


@router.post("/", status_code=201)
def generar_informe(
    data: InformeNotasRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.registrar")),
):
    contenido = armar_contenido(db, data)
    es_final = data.tipo == "final"

    if es_final:
        final_existente = db.query(InformeNotas).filter(
            InformeNotas.id_programa_version_edicion == data.id_programa_version_edicion,
            InformeNotas.tipo == "final",
        ).first()
        if final_existente:
            raise HTTPException(
                status_code=400,
                detail="El informe final de esta edicion ya fue generado",
            )

    numero_tanda = _siguiente_tanda(db, data.id_programa_version_edicion)
    alumnos_ids = sorted({
        a["id_alumno"]
        for c in contenido["carreras"]
        for m in c["modulos"]
        for a in m["alumnos"]
    })

    informe = InformeNotas(
        id_programa_version_edicion=data.id_programa_version_edicion,
        numero_tanda=numero_tanda,
        tipo=data.tipo,
        fecha_emision=date.today(),
        generado_at=datetime.now(timezone.utc),
        alumnos_ids=alumnos_ids,
        contenido=contenido,
        estado="enviado",
    )
    db.add(informe)
    db.flush()

    cert_count = 0
    if es_final:
        pve, _, _ = resolver_edicion(db, data.id_programa_version_edicion)
        dpas = {d.id_alumno: d for d in _dpas_por_edicion(db, data.id_programa_version_edicion)}
        elegibles = _elegibles_final(db, data.id_programa_version_edicion, contenido, dpas)
        for alumno_id in elegibles:
            db.add(CertificadoNotas(
                id_alumno=alumno_id,
                id_programa_version_edicion=data.id_programa_version_edicion,
                id_informe=informe.id_informe,
                fecha_emision=date.today(),
            ))
            cert_count += 1

    db.commit()
    db.refresh(informe)
    return {**_serializar_informe(informe, cert_count), "contenido": informe.contenido}


def _dpas_por_edicion(db: Session, id_edicion: int):
    from models.detalle_programa_alumno import DetalleProgramaAlumno
    return db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_programa_version_edicion == id_edicion
    ).all()


def _elegibles_final(db: Session, id_edicion: int, contenido: dict, dpas_map: dict) -> list[int]:
    dpas = [d for d in dpas_map.values()
            if d.estado in ("inscrito", "incorporado", "finalizado", "graduado")]
    if not dpas:
        return []
    nota_map = {}
    import textwrap
    # construir mapa desde el contenido congelado (matriz por carrera)
    for c in contenido["carreras"]:
        for f in c["matriz_filas"]:
            id_dpa = f["id_detalle_programa_alumno"]
            for id_dpm, nota in zip(
                [col["id_detalle_programa_modulo"] for col in c["matriz_columnas"]],
                f["notas"],
            ):
                if nota is not None:
                    nota_map[(id_dpa, id_dpm)] = nota
    id_dmps = []
    for c in contenido["carreras"]:
        for col in c["matriz_columnas"]:
            if col["id_detalle_programa_modulo"] not in id_dmps:
                id_dmps.append(col["id_detalle_programa_modulo"])
    eleg = calcular_elegibilidad(db, id_edicion, dpas, nota_map, id_dmps)
    return [d.id_alumno for d in dpas if eleg.get(d.id_detalle_programa_alumno, {}).get("elegible")]


@router.get("/por-edicion/{id_edicion}")
def informes_por_edicion(
    id_edicion: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver")),
):
    informes = db.query(InformeNotas).filter(
        InformeNotas.id_programa_version_edicion == id_edicion
    ).order_by(InformeNotas.numero_tanda.desc()).all()
    return [
        _serializar_informe(i, _certificados_por_informe(db, i.id_informe))
        for i in informes
    ]


@router.get("/{id_informe}")
def obtener_informe(
    id_informe: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver")),
):
    informe = db.query(InformeNotas).filter(
        InformeNotas.id_informe == id_informe
    ).first()
    if not informe:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    return _serializar_informe(informe, _certificados_por_informe(db, id_informe))


@router.get("/elegibles/{id_edicion}")
def alumnos_elegibles(
    id_edicion: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver")),
):
    pve, _, _ = resolver_edicion(db, id_edicion)
    dpas = _dpas_por_edicion(db, id_edicion)
    dpas = [d for d in dpas if d.estado in ("inscrito", "incorporado", "finalizado", "graduado")]
    nota_map = {}
    from models.nota import Nota
    for n in db.query(Nota).filter(Nota.id_detalle_programa_alumno.in_(
        [d.id_detalle_programa_alumno for d in dpas]
    )).all():
        nota_map[(n.id_detalle_programa_alumno, n.id_detalle_programa_modulo)] = float(n.nota)
    from models.detalle_programa_modulo import DetalleProgramaModulo
    all_dmps = [d.id_detalle_programa_modulo for d in db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == id_edicion
    ).all()]
    eleg = calcular_elegibilidad(db, id_edicion, dpas, nota_map, all_dmps)
    resultado = []
    for d in dpas:
        det = eleg.get(d.id_detalle_programa_alumno, {})
        resultado.append({
            "id_alumno": d.id_alumno,
            "id_detalle_programa_alumno": d.id_detalle_programa_alumno,
            "nombre": d.alumno.nombre,
            "apellido": d.alumno.apellido,
            "ci": d.alumno.ci,
            "elegible": det.get("elegible", False),
            "motivo_exclusion": det.get("motivo_exclusion"),
        })
    return {"id_programa_version_edicion": id_edicion, "total_elegibles": sum(1 for r in resultado if r["elegible"]), "alumnos": resultado}
