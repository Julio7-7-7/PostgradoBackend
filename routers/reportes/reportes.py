from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_permiso
from models.alumno import Alumno
from models.carrera import Carrera
from models.certificado_notas import CertificadoNotas
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.informe_notas import InformeNotas
from models.modulo import Modulo
from models.nota import Nota
from models.programa import Programa
from models.programa_version import ProgramaVersion
from models.programa_version_edicion import ProgramaVersionEdicion
from models.transaccion_pago import TransaccionPago
from routers.pagos.matriz import _estado_financiero
from schemas.auth import UserResponse
from schemas.enums import clasificar_nota, NotaCalificacion

router = APIRouter(
    prefix="/reportes",
    tags=["Reportes"],
    dependencies=[Depends(get_current_user)],
)

ESTADOS_CON_DEUDA = {"inscrito", "incorporado", "finalizado", "graduado"}
ESTADOS_POBLACION_LABEL = {
    "inscrito": "Inscritos",
    "incorporado": "Incorporados",
    "finalizado": "Finalizados",
    "graduado": "Graduados",
    "retirado": "Retirados",
    "abandono": "Abandonos",
}


def _validar_rango(desde: str | None, hasta: str | None) -> tuple[date, date]:
    hoy = date.today()
    d = date.fromisoformat(desde) if desde else hoy.replace(year=hoy.year - 1)
    h = date.fromisoformat(hasta) if hasta else hoy
    if d > h:
        raise HTTPException(status_code=400, detail="La fecha 'desde' no puede ser mayor que 'hasta'")
    return d, h


def _nombre_programa(edicion: ProgramaVersionEdicion) -> str:
    if edicion and edicion.programa_version and edicion.programa_version.programa:
        return edicion.programa_version.programa.nombre_programa
    return "Programa"


def _carrera_nombre(db: Session, detalle: DetalleProgramaAlumno) -> str | None:
    if detalle.id_carrera:
        c = db.query(Carrera).filter(Carrera.id_carrera == detalle.id_carrera).first()
        return c.nombre if c else None
    return None


@router.get("/opciones")
def opciones_reportes(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("reportes.ver")),
):
    programas = db.query(Programa).order_by(Programa.nombre_programa).all()
    carreras = db.query(Carrera).order_by(Carrera.nombre).all()
    ediciones = db.query(ProgramaVersionEdicion).order_by(
        ProgramaVersionEdicion.anio.desc(),
        ProgramaVersionEdicion.semestre.desc(),
    ).all()

    cabeceras = []
    for e in ediciones:
        pv = e.programa_version
        prog = pv.programa if pv else None
        cabeceras.append({
            "id_programa_version_edicion": e.id_programa_version_edicion,
            "programa": prog.nombre_programa if prog else "Programa",
            "version": pv.version if pv else None,
            "edicion": e.edicion,
            "anio": e.anio,
            "semestre": e.semestre,
            "modalidad": e.modalidad,
            "estado": e.estado,
            "fecha_inicio": str(e.fecha_inicio) if e.fecha_inicio else None,
            "fecha_fin": str(e.fecha_fin) if e.fecha_fin else None,
        })

    return {
        "programas": [
            {
                "id_programa": p.id_programa,
                "nombre": p.nombre_programa,
                "versiones": [
                    {
                        "id_programa_version": v.id_programa_version,
                        "version": v.version,
                        "ediciones": [
                            {
                                "id_programa_version_edicion": e.id_programa_version_edicion,
                                "edicion": e.edicion,
                                "anio": e.anio,
                                "semestre": e.semestre,
                                "modalidad": e.modalidad,
                                "estado": e.estado,
                                "fecha_inicio": str(e.fecha_inicio) if e.fecha_inicio else None,
                                "fecha_fin": str(e.fecha_fin) if e.fecha_fin else None,
                            }
                            for e in v.ediciones
                        ],
                    }
                    for v in p.versiones
                ],
            }
            for p in programas
        ],
        "carreras": [{"id_carrera": c.id_carrera, "nombre": c.nombre, "sigla": c.sigla} for c in carreras],
        "ediciones": cabeceras,
    }


def _ingresos(db: Session, desde: date, hasta: date, id_carrera: int | None):
    query = db.query(
        TransaccionPago,
        DetalleProgramaAlumno,
        ProgramaVersionEdicion,
    ).join(
        DetalleProgramaAlumno,
        DetalleProgramaAlumno.id_detalle_programa_alumno == TransaccionPago.id_detalle_programa_alumno,
    ).join(
        ProgramaVersionEdicion,
        ProgramaVersionEdicion.id_programa_version_edicion == DetalleProgramaAlumno.id_programa_version_edicion,
    ).filter(
        TransaccionPago.estado == "confirmado",
        TransaccionPago.fecha_pago >= desde,
        TransaccionPago.fecha_pago <= hasta,
    )

    if id_carrera:
        query = query.filter(DetalleProgramaAlumno.id_carrera == id_carrera)

    filas = query.all()

    total = 0.0
    por_mes: dict[str, float] = {}
    por_edicion: dict[str, float] = {}
    por_concepto = {"matricula": 0.0, "cuotas": 0.0}
    matricula_esperado = 0.0
    matricula_pagado = 0.0

    for t, dpa, e in filas:
        monto = float(t.monto_total)
        total += monto
        clave_mes = str(t.fecha_pago)[:7]
        por_mes[clave_mes] = por_mes.get(clave_mes, 0.0) + monto

        prog = _nombre_programa(e)
        por_edicion[prog] = por_edicion.get(prog, 0.0) + monto

    return {
        "total": round(total, 2),
        "por_mes": [{"periodo": k, "monto": round(v, 2)} for k, v in sorted(por_mes.items())],
        "por_edicion": [{"programa": k, "monto": round(v, 2)} for k, v in sorted(por_edicion.items())],
    }


def _deudores_snapshot(db: Session, id_carrera: int | None):
    query = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.estado.in_(ESTADOS_CON_DEUDA)
    )
    if id_carrera:
        query = query.filter(DetalleProgramaAlumno.id_carrera == id_carrera)

    detalles = query.all()
    dpa_ids = [d.id_detalle_programa_alumno for d in detalles]

    edicion_ids = {d.id_programa_version_edicion for d in detalles}
    ediciones = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion.in_(edicion_ids)
    ).all() if edicion_ids else []
    edicion_por_id = {e.id_programa_version_edicion: e for e in ediciones}

    modulos_por_edicion: dict[int, list] = {}
    for e in ediciones:
        modulos_por_edicion[e.id_programa_version_edicion] = db.query(DetalleProgramaModulo).filter(
            DetalleProgramaModulo.id_programa_version_edicion == e.id_programa_version_edicion
        ).order_by(DetalleProgramaModulo.orden).all()

    alumnos_ids = {d.id_alumno for d in detalles}
    alumnos = db.query(Alumno).filter(Alumno.id_alumno.in_(alumnos_ids)).all() if alumnos_ids else []
    alumno_por_id = {a.id_alumno: a for a in alumnos}

    deuda_total = 0.0
    deudores: list[dict] = []
    deuda_por_programa: dict[str, float] = {}

    for detalle in detalles:
        edicion = edicion_por_id.get(detalle.id_programa_version_edicion)
        if not edicion:
            continue
        dpm_list = modulos_por_edicion.get(edicion.id_programa_version_edicion, [])
        precio = float(edicion.precio or 0)
        matricula_monto = float(edicion.matricula or 0)
        est = _estado_financiero(db, detalle, dpm_list, precio, matricula_monto)
        total_esperado = est["matricula_esperado"] + est["total_esperado_cuotas"] + est["otros_pagado"]
        saldo = round(total_esperado - est["total_pagado"], 2)
        if saldo <= 0:
            continue

        deuda_total += saldo
        alumno = alumno_por_id.get(detalle.id_alumno)
        prog = _nombre_programa(edicion)
        deuda_por_programa[prog] = round(deuda_por_programa.get(prog, 0.0) + saldo, 2)
        deudores.append({
            "id_detalle_programa_alumno": detalle.id_detalle_programa_alumno,
            "id_alumno": detalle.id_alumno,
            "nombre": alumno.nombre if alumno else "N/A",
            "apellido": alumno.apellido if alumno else "N/A",
            "ci": alumno.ci if alumno else None,
            "celular": alumno.celular if alumno else None,
            "correo": alumno.correo if alumno else None,
            "carrera": _carrera_nombre(db, detalle),
            "programa": prog,
            "estado": detalle.estado,
            "saldo": saldo,
        })

    por_carrera: dict[str, dict] = {}
    for d in deudores:
        clave = d["carrera"] or "Sin carrera"
        grupo = por_carrera.setdefault(clave, {"carrera": clave, "deuda": 0.0, "cantidad": 0, "deudores": []})
        grupo["deuda"] = round(grupo["deuda"] + d["saldo"], 2)
        grupo["cantidad"] += 1
        grupo["deudores"].append(d)
    for g in por_carrera.values():
        g["deudores"].sort(key=lambda x: (x["apellido"], x["nombre"]))

    return {
        "deuda_total": round(deuda_total, 2),
        "cantidad_deudores": len(deudores),
        "deuda_por_programa": [{"programa": k, "deuda": v} for k, v in sorted(deuda_por_programa.items())],
        "por_carrera": [
            {"carrera": k, "deuda": v["deuda"], "cantidad": v["cantidad"], "deudores": v["deudores"]}
            for k, v in por_carrera.items()
        ],
        "deudores": deudores,
    }


@router.get("/economico")
def reporte_economico(
    desde: str | None = Query(None),
    hasta: str | None = Query(None),
    id_carrera: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("reportes.ver")),
):
    d, h = _validar_rango(desde, hasta)
    ingresos = _ingresos(db, d, h, id_carrera)
    deudores = _deudores_snapshot(db, id_carrera)
    return {
        "desde": str(d),
        "hasta": str(h),
        "carrera": id_carrera,
        "ingresos": ingresos,
        "deuda": {
            "total": deudores["deuda_total"],
            "cantidad_deudores": deudores["cantidad_deudores"],
            "por_programa": deudores["deuda_por_programa"],
        },
        "deudores_por_carrera": deudores["por_carrera"],
        "deudores": deudores["deudores"],
    }


@router.get("/poblacion")
def reporte_poblacion(
    desde: str | None = Query(None),
    hasta: str | None = Query(None),
    id_programa: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("reportes.ver")),
):
    d, h = _validar_rango(desde, hasta)

    query = db.query(DetalleProgramaAlumno).join(
        ProgramaVersionEdicion,
        ProgramaVersionEdicion.id_programa_version_edicion == DetalleProgramaAlumno.id_programa_version_edicion,
    ).filter(
        DetalleProgramaAlumno.fecha_inscripcion.isnot(None),
        DetalleProgramaAlumno.fecha_inscripcion >= d,
        DetalleProgramaAlumno.fecha_inscripcion <= h,
    )
    if id_programa:
        ids = [
            r[0]
            for r in db.query(ProgramaVersionEdicion.id_programa_version_edicion).join(
                ProgramaVersion,
                ProgramaVersion.id_programa_version == ProgramaVersionEdicion.id_programa_version,
            ).filter(ProgramaVersion.id_programa == id_programa).all()
        ]
        query = query.filter(
            DetalleProgramaAlumno.id_programa_version_edicion.in_(ids) if ids else DetalleProgramaAlumno.id_programa_version_edicion == -1
        )

    detalles = query.all()

    por_estado: dict[str, int] = {k: 0 for k in ESTADOS_POBLACION_LABEL}
    incorporaciones = 0
    por_programa: dict[str, dict] = {}
    por_mes: dict[str, int] = {}

    for detalle in detalles:
        estado = detalle.estado
        if estado in por_estado:
            por_estado[estado] += 1
        else:
            por_estado.setdefault(estado, 0)
            por_estado[estado] += 1

        if detalle.es_incorporacion:
            incorporaciones += 1

        edicion = db.query(ProgramaVersionEdicion).filter(
            ProgramaVersionEdicion.id_programa_version_edicion == detalle.id_programa_version_edicion
        ).first()
        prog = _nombre_programa(edicion) if edicion else "Programa"
        g = por_programa.setdefault(prog, {"programa": prog, "cantidad": 0, "retirados": 0, "graduados": 0})
        g["cantidad"] += 1
        if detalle.estado == "retirado":
            g["retirados"] += 1
        if detalle.estado == "graduado":
            g["graduados"] += 1

        if detalle.fecha_inscripcion:
            clave_mes = str(detalle.fecha_inscripcion)[:7]
            por_mes[clave_mes] = por_mes.get(clave_mes, 0) + 1

    egresados_informe = db.query(CertificadoNotas).filter(
        CertificadoNotas.fecha_emision >= d,
        CertificadoNotas.fecha_emision <= h,
        CertificadoNotas.procedencia == "informe",
    ).count()

    egresados_profesional = db.query(CertificadoNotas).filter(
        CertificadoNotas.fecha_emision >= d,
        CertificadoNotas.fecha_emision <= h,
        CertificadoNotas.procedencia != "informe",
    ).count()

    return {
        "desde": str(d),
        "hasta": str(h),
        "total": len(detalles),
        "por_estado": [{"estado": k, "label": ESTADOS_POBLACION_LABEL.get(k, k), "cantidad": v} for k, v in por_estado.items()],
        "incorporaciones": incorporaciones,
        "egresados": {
            "educacion_continua": egresados_informe,
            "profesionales": egresados_profesional,
            "total": egresados_informe + egresados_profesional,
        },
        "por_programa": sorted(por_programa.values(), key=lambda x: -x["cantidad"]),
        "evolucion": [{"periodo": k, "cantidad": v} for k, v in sorted(por_mes.items())],
    }


@router.get("/rendimiento")
def reporte_rendimiento(
    desde: str | None = Query(None),
    hasta: str | None = Query(None),
    id_programa: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("reportes.ver")),
):
    d, h = _validar_rango(desde, hasta)

    query = db.query(Nota).filter(Nota.fecha >= d, Nota.fecha <= h)
    if id_programa:
        ediciones = db.query(ProgramaVersionEdicion.id_programa_version_edicion).join(
            ProgramaVersion,
            ProgramaVersion.id_programa_version == ProgramaVersionEdicion.id_programa_version,
        ).filter(ProgramaVersion.id_programa == id_programa).all()
        ids = [r[0] for r in ediciones]
        query = query.join(
            DetalleProgramaModulo,
            DetalleProgramaModulo.id_detalle_programa_modulo == Nota.id_detalle_programa_modulo,
        ).filter(
            DetalleProgramaModulo.id_programa_version_edicion.in_(ids) if ids else DetalleProgramaModulo.id_programa_version_edicion == -1,
        )

    notas = query.all()

    if not notas:
        return {
            "desde": str(d),
            "hasta": str(h),
            "total_notas": 0,
            "promedio_general": 0,
            "por_clasificacion": [],
            "por_modulo": [],
            "aprobados": 0,
            "reprobados": 0,
        }

    total = 0.0
    clasificacion: dict[str, int] = {}
    por_modulo: dict[int, dict] = {}
    aprobados = 0
    reprobados = 0

    for n in notas:
        val = float(n.nota)
        total += val
        c = clasificar_nota(val)
        clasificacion[c.value] = clasificacion.get(c.value, 0) + 1

        if c in (NotaCalificacion.SUFICIENTE, NotaCalificacion.BUENO, NotaCalificacion.DISTINGUIDO, NotaCalificacion.SOBRESALIENTE):
            aprobados += 1
        else:
            reprobados += 1

        dpm = db.query(DetalleProgramaModulo).filter(
            DetalleProgramaModulo.id_detalle_programa_modulo == n.id_detalle_programa_modulo
        ).first()
        if dpm:
            g = por_modulo.setdefault(dpm.id_detalle_programa_modulo, {
                "id_detalle_programa_modulo": dpm.id_detalle_programa_modulo,
                "orden": dpm.orden,
                "nombre": "",
                "suma": 0.0,
                "cantidad": 0,
                "aprobados": 0,
                "reprobados": 0,
            })
            mod = db.query(Modulo).filter(Modulo.id_modulo == dpm.id_modulo).first()
            g["nombre"] = mod.nombre_modulo if mod else f"Módulo #{dpm.id_modulo}"
            g["suma"] += val
            g["cantidad"] += 1
            if c in (NotaCalificacion.SUFICIENTE, NotaCalificacion.BUENO, NotaCalificacion.DISTINGUIDO, NotaCalificacion.SOBRESALIENTE):
                g["aprobados"] += 1
            else:
                g["reprobados"] += 1

    for g in por_modulo.values():
        g["promedio"] = round(g["suma"] / g["cantidad"], 2)

    orden_clasif = ["sobresaliente", "distinguido", "bueno", "suficiente", "insuficiente", "abandono"]
    return {
        "desde": str(d),
        "hasta": str(h),
        "total_notas": len(notas),
        "promedio_general": round(total / len(notas), 2),
        "por_clasificacion": [
            {"clasificacion": c, "cantidad": clasificacion.get(c, 0)} for c in orden_clasif
        ],
        "por_modulo": sorted(por_modulo.values(), key=lambda x: x["orden"]),
        "aprobados": aprobados,
        "reprobados": reprobados,
    }
