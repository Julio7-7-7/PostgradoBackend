import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_permiso
from models.administrativo import Administrativo
from models.alumno import Alumno
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.historial_inscripcion import HistorialInscripcion
from models.modulo import Modulo
from models.nota import Nota
from models.orden_pago import OrdenPago
from models.pago import Pago
from models.programa_version_edicion import ProgramaVersionEdicion
from models.transaccion_pago import TransaccionPago
from models.usuario import Usuario
from schemas.auth import UserResponse
from schemas.enums import clasificar_nota

router = APIRouter(
    prefix="/pagos",
    tags=["Pagos"],
    dependencies=[Depends(get_current_user)]
)

BECA_PERDIDA_CALIFICACIONES = {"insuficiente", "abandono"}


def _descuento_porcentaje(detalle) -> float:
    return max(0.0, min(100.0, float(detalle.descuento_aplicado or 0)))


def _contexto(db: Session, detalle: DetalleProgramaAlumno) -> dict:
    alumno = db.query(Alumno).filter(Alumno.id_alumno == detalle.id_alumno).first()
    edicion = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == detalle.id_programa_version_edicion
    ).first()
    programa = None
    if edicion and edicion.programa_version and edicion.programa_version.programa:
        programa = edicion.programa_version.programa.nombre_programa
    return {
        "alumno": {
            "id_alumno": detalle.id_alumno,
            "nombre": alumno.nombre if alumno else "N/A",
            "apellido": alumno.apellido if alumno else "N/A",
            "ci": alumno.ci if alumno else None,
        },
        "edicion": {
            "programa": programa,
            "edicion": edicion.edicion if edicion else None,
            "anio": edicion.anio if edicion else None,
            "semestre": edicion.semestre if edicion else None,
        },
    }


def _serializar_orden(db: Session, orden: OrdenPago) -> dict:
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == orden.id_detalle_programa_alumno
    ).first()
    contexto = _contexto(db, detalle) if detalle else {"alumno": None, "edicion": None}
    return {
        "id_orden_pago": orden.id_orden_pago,
        "numero": orden.numero,
        "id_detalle_programa_alumno": orden.id_detalle_programa_alumno,
        "fecha_emision": str(orden.fecha_emision),
        "monto_total": float(orden.monto_total),
        "items": orden.items,
        "estado": orden.estado,
        "motivo_anulacion": orden.motivo_anulacion,
        "anulado_por_id_usuario": orden.anulado_por_id_usuario,
        "anulado_fecha": orden.anulado_fecha.isoformat() if orden.anulado_fecha else None,
        "creado_por_id_usuario": orden.creado_por_id_usuario,
        "created_at": orden.created_at.isoformat() if orden.created_at else None,
        "updated_at": orden.updated_at.isoformat() if orden.updated_at else None,
        "id_transaccion": orden.transaccion.id_transaccion if orden.transaccion else None,
        **contexto,
    }


def _origenes_transitivos(db: Session, id_destino: int) -> list[int]:
    """DPAs de ediciones anteriores del alumno (migración/incorporación), transitivo."""
    cola = [id_destino]
    vistos = set()
    orden: list[int] = []
    while cola:
        d = cola.pop(0)
        if d in vistos:
            continue
        vistos.add(d)
        filas = db.query(HistorialInscripcion.id_detalle_origen).filter(
            HistorialInscripcion.id_detalle_destino == d
        ).all()
        for (o,) in filas:
            if o not in vistos:
                orden.append(o)
                cola.append(o)
    return orden


def _expecteds_cuotas(precio: float, factor: float, dpm_list: list) -> tuple[dict, float]:
    total_cuotas = max(0.0, float(precio or 0)) * factor
    n = len(dpm_list)
    expecteds: dict[int, float] = {}
    if n == 0:
        return expecteds, 0.0
    base = math.floor(total_cuotas / n * 100) / 100
    for i, dpm in enumerate(dpm_list):
        if i == n - 1:
            expecteds[dpm.id_detalle_programa_modulo] = round(total_cuotas - base * (n - 1), 2)
        else:
            expecteds[dpm.id_detalle_programa_modulo] = base
    return expecteds, round(sum(expecteds.values()), 2)


def _cargar_movimientos(db: Session, dpa_ids: list[int]) -> list[tuple[Pago, TransaccionPago]]:
    """Pares (fila de pago, transacción) para los DPAs dados."""
    if not dpa_ids:
        return []
    filas = (
        db.query(Pago, TransaccionPago)
        .join(TransaccionPago, TransaccionPago.id_transaccion == Pago.id_transaccion)
        .filter(TransaccionPago.id_detalle_programa_alumno.in_(dpa_ids))
        .all()
    )
    return [(p, t) for p, t in filas]


def _estado_financiero(db: Session, detalle, dpm_list: list, precio: float, matricula: float = 0.0) -> dict:
    """Expecteds + pagado por cuota/matrícula para un alumno (incluye pagos de ediciones origen)."""
    dpm_por_id = {d.id_detalle_programa_modulo: d for d in dpm_list}
    dpm_dest_por_id_modulo = {d.id_modulo: d for d in dpm_list}
    dpm_dest_por_orden = {d.orden: d for d in dpm_list}

    beca_activa = True
    beca_motivo = None
    notas = db.query(Nota).filter(
        Nota.id_detalle_programa_alumno == detalle.id_detalle_programa_alumno
    ).all()
    for n in notas:
        dpm = dpm_por_id.get(n.id_detalle_programa_modulo)
        if dpm and dpm.estado == "finalizado":
            cal = clasificar_nota(float(n.nota)).value
            if cal in BECA_PERDIDA_CALIFICACIONES:
                beca_activa = False
                beca_motivo = (
                    f"{'Reprobó' if cal == 'insuficiente' else 'Abandonó'} el Módulo {dpm.orden}"
                    f" — todas las cuotas pasan a precio pleno"
                )
                break

    desc = _descuento_porcentaje(detalle)
    factor = (1 - desc / 100.0) if beca_activa else 1.0
    expecteds, total_esperado_cuotas = _expecteds_cuotas(precio, factor, dpm_list)

    origen_ids = _origenes_transitivos(db, detalle.id_detalle_programa_alumno)
    origin_dpm_por_id: dict[int, DetalleProgramaModulo] = {}
    origin_edicion_por_dpa: dict[int, dict] = {}
    if origen_ids:
        origin_dpas = db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_detalle_programa_alumno.in_(origen_ids)
        ).all() if origen_ids else []
        origin_edicion_ids = {d.id_programa_version_edicion for d in origin_dpas}
        origin_ediciones = db.query(ProgramaVersionEdicion).filter(
            ProgramaVersionEdicion.id_programa_version_edicion.in_(origin_edicion_ids)
        ).all() if origin_edicion_ids else []
        edicion_por_id = {e.id_programa_version_edicion: e for e in origin_ediciones}
        for d in origin_dpas:
            e = edicion_por_id.get(d.id_programa_version_edicion)
            origin_edicion_por_dpa[d.id_detalle_programa_alumno] = (
                {"edicion": e.edicion, "anio": e.anio, "semestre": e.semestre} if e else None
            )
        origin_dpm_ids = {p.id_detalle_programa_modulo for p, _ in _cargar_movimientos(db, origen_ids) if p.id_detalle_programa_modulo}
        origin_dpms = db.query(DetalleProgramaModulo).filter(
            DetalleProgramaModulo.id_detalle_programa_modulo.in_(origin_dpm_ids)
        ).all() if origin_dpm_ids else []
        origin_dpm_por_id = {d.id_detalle_programa_modulo: d for d in origin_dpms}

    pagado_por_dpm: dict[int, float] = {d.id_detalle_programa_modulo: 0.0 for d in dpm_list}
    cuota_pagos: dict[int, list] = {d.id_detalle_programa_modulo: [] for d in dpm_list}
    matricula_pagos: list = []
    otros_pagos: list = []
    total_pagado = 0.0

    def _entry(p: Pago, t: TransaccionPago, es_origen: bool) -> dict:
        return {
            "id_pago": p.id_pago,
            "id_transaccion": t.id_transaccion,
            "monto": float(p.monto),
            "fecha_pago": str(t.fecha_pago),
            "concepto": p.concepto,
            "estado": t.estado,
            "comprobante": t.comprobante,
            "origen": (origin_edicion_por_dpa.get(t.id_detalle_programa_alumno) if es_origen else None),
        }

    def _target_de(p: Pago, es_origen: bool):
        if p.id_detalle_programa_modulo is None:
            return "matricula"
        if not es_origen:
            return p.id_detalle_programa_modulo
        odpm = origin_dpm_por_id.get(p.id_detalle_programa_modulo)
        if odpm:
            dest = dpm_dest_por_id_modulo.get(odpm.id_modulo)
            if dest:
                return dest.id_detalle_programa_modulo
            dest2 = dpm_dest_por_orden.get(odpm.orden)
            if dest2:
                return dest2.id_detalle_programa_modulo
        return "otros"

    def _aplicar(p: Pago, t: TransaccionPago, es_origen: bool):
        nonlocal total_pagado
        target = _target_de(p, es_origen)
        entry = _entry(p, t, es_origen)
        if target == "matricula":
            matricula_pagos.append(entry)
        elif target not in cuota_pagos:
            otros_pagos.append(entry)
        else:
            cuota_pagos[target].append(entry)
        if t.estado != "confirmado":
            return
        total_pagado += float(p.monto)
        if target != "matricula" and target in pagado_por_dpm:
            pagado_por_dpm[target] += float(p.monto)

    movimientos = _cargar_movimientos(db, [detalle.id_detalle_programa_alumno])
    for p, t in movimientos:
        _aplicar(p, t, False)
    movimientos_origen = _cargar_movimientos(db, origen_ids)
    for p, t in movimientos_origen:
        _aplicar(p, t, True)

    matricula_pagado = sum(
        float(p.monto)
        for p, t in movimientos + movimientos_origen
        if t.estado == "confirmado" and p.id_detalle_programa_modulo is None
    )
    otros_pagado = sum(e["monto"] for e in otros_pagos if e["estado"] == "confirmado")

    return {
        "expecteds": expecteds,
        "total_esperado_cuotas": total_esperado_cuotas,
        "matricula_esperado": float(matricula or 0),
        "matricula_pagado": matricula_pagado,
        "matricula_pagos": matricula_pagos,
        "pagado_por_dpm": pagado_por_dpm,
        "cuota_pagos": cuota_pagos,
        "otros_pagado": otros_pagado,
        "otros_pagos": otros_pagos,
        "beca_activa": beca_activa,
        "beca_motivo": beca_motivo,
        "total_pagado": round(total_pagado, 2),
    }


def _plan_exacto(db: Session, detalle, dpm_list: list, precio: float, matricula: float, cubre_matricula: bool, cantidad_modulos: int):
    """Plan exacto de una orden/pago: matrícula completa (si pendiente y pedida) +
    N cuotas íntegras y contiguas desde la primera pendiente. Sin montos libres
    ni cuotas parciales (descuento/beca del estado financiero)."""
    est = _estado_financiero(db, detalle, dpm_list, precio, matricula)

    resto_mat = max(0.0, est["matricula_esperado"] - est["matricula_pagado"])

    cuotas_pendientes: list[tuple] = []
    for dpm in dpm_list:
        resto = max(
            0.0,
            est["expecteds"].get(dpm.id_detalle_programa_modulo, 0.0)
            - est["pagado_por_dpm"].get(dpm.id_detalle_programa_modulo, 0.0),
        )
        if resto <= 0:
            continue
        cuotas_pendientes.append((dpm, resto))

    if resto_mat > 0 and not cubre_matricula and cantidad_modulos > 0:
        raise HTTPException(
            status_code=400,
            detail="La matrícula pendiente debe incluirse en la orden",
        )

    if cantidad_modulos > len(cuotas_pendientes):
        raise HTTPException(
            status_code=400,
            detail=f"Solo hay {len(cuotas_pendientes)} cuota(s) pendiente(s) por cobrar",
        )

    for dpm, resto in cuotas_pendientes[:cantidad_modulos]:
        esperado = est["expecteds"].get(dpm.id_detalle_programa_modulo, 0.0)
        if abs(resto - esperado) > 0.005:
            raise HTTPException(
                status_code=400,
                detail=f"La cuota {dpm.orden} tiene un pago parcial previo; debe completarse en su totalidad",
            )

    asignaciones: list[tuple] = []
    if cubre_matricula and resto_mat > 0:
        asignaciones.append((None, resto_mat))
    for dpm, resto in cuotas_pendientes[:cantidad_modulos]:
        asignaciones.append((dpm, resto))

    if not asignaciones:
        raise HTTPException(status_code=400, detail="La orden no cubre ningún concepto")

    monto_total = round(sum(m for _, m in asignaciones), 2)
    return asignaciones, monto_total


def _serializar_pago(p: Pago) -> dict:
    return {
        "id_pago": p.id_pago,
        "id_transaccion": p.id_transaccion,
        "id_detalle_programa_modulo": p.id_detalle_programa_modulo,
        "monto": float(p.monto),
        "concepto": p.concepto,
    }


def _nombre_usuario(db: Session, id_usuario: int | None) -> str | None:
    if not id_usuario:
        return None
    adm = db.query(Administrativo).filter(Administrativo.id_usuario == id_usuario).first()
    if adm:
        return f"{adm.nombre} {adm.apellido}".strip()
    usr = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    return usr.email if usr else None


@router.get("/por-edicion/{id_edicion}")
def pagos_por_edicion(
    id_edicion: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver"))
):
    edicion = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id_edicion
    ).first()
    if not edicion:
        raise HTTPException(status_code=404, detail="Edición no encontrada")

    precio = float(edicion.precio or 0)
    matricula = float(edicion.matricula or 0)

    dpm_list = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == id_edicion
    ).order_by(DetalleProgramaModulo.orden).all()

    modulos = []
    for dpm in dpm_list:
        mod = db.query(Modulo).filter(Modulo.id_modulo == dpm.id_modulo).first()
        modulos.append({
            "id_detalle_programa_modulo": dpm.id_detalle_programa_modulo,
            "id_modulo": dpm.id_modulo,
            "nombre": mod.nombre_modulo if mod else f"Módulo #{dpm.id_modulo}",
            "sigla": mod.sigla if mod else "",
            "orden": dpm.orden,
        })

    detalles = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_programa_version_edicion == id_edicion
    ).order_by(DetalleProgramaAlumno.id_detalle_programa_alumno).all()

    dpa_ids = [d.id_detalle_programa_alumno for d in detalles]
    ordenes_emitidas: dict[int, dict] = {}
    if dpa_ids:
        activas = db.query(OrdenPago).filter(
            OrdenPago.id_detalle_programa_alumno.in_(dpa_ids),
            OrdenPago.estado == "emitida",
        ).all()
        for o in activas:
            ordenes_emitidas[o.id_detalle_programa_alumno] = _serializar_orden(db, o)

    resultado = []
    for detalle in detalles:
        alumno = db.query(Alumno).filter(Alumno.id_alumno == detalle.id_alumno).first()
        est = _estado_financiero(db, detalle, dpm_list, precio, matricula)

        total_esperado = round(est["matricula_esperado"] + est["total_esperado_cuotas"], 2)
        pct_total = round(min(100.0, est["total_pagado"] / total_esperado * 100), 1) if total_esperado else 0.0

        cuotas = []
        for dpm in dpm_list:
            esperado = est["expecteds"].get(dpm.id_detalle_programa_modulo, 0.0)
            pagado = round(est["pagado_por_dpm"].get(dpm.id_detalle_programa_modulo, 0.0), 2)
            cuotas.append({
                "id_detalle_programa_modulo": dpm.id_detalle_programa_modulo,
                "id_modulo": dpm.id_modulo,
                "orden": dpm.orden,
                "nombre": next((m["nombre"] for m in modulos if m["id_detalle_programa_modulo"] == dpm.id_detalle_programa_modulo), ""),
                "sigla": next((m["sigla"] for m in modulos if m["id_detalle_programa_modulo"] == dpm.id_detalle_programa_modulo), ""),
                "esperado": esperado,
                "pagado": pagado,
                "pct": round(min(100.0, pagado / esperado * 100), 1) if esperado else 0.0,
                "pagos": est["cuota_pagos"].get(dpm.id_detalle_programa_modulo, []),
            })

        matricula_pagado = round(est["matricula_pagado"], 2)
        matricula_esperado = est["matricula_esperado"]

        resultado.append({
            "id_detalle_programa_alumno": detalle.id_detalle_programa_alumno,
            "orden_activa": ordenes_emitidas.get(detalle.id_detalle_programa_alumno),
            "alumno": {
                "id_alumno": alumno.id_alumno if alumno else None,
                "nombre": alumno.nombre if alumno else "N/A",
                "apellido": alumno.apellido if alumno else "N/A",
                "ci": alumno.ci if alumno else None,
            } if alumno else None,
            "estado": detalle.estado,
            "descuento_aplicado": _descuento_porcentaje(detalle),
            "beca_activa": est["beca_activa"],
            "beca_motivo": est["beca_motivo"],
            "matricula": {
                "esperado": matricula_esperado,
                "pagado": matricula_pagado,
                "pct": round(min(100.0, matricula_pagado / matricula_esperado * 100), 1) if matricula_esperado else 0.0,
                "pagos": est["matricula_pagos"],
            },
            "cuotas": cuotas,
            "otros": {
                "pagado": round(est["otros_pagado"], 2),
                "pagos": est["otros_pagos"],
            },
            "total_esperado": total_esperado,
            "total_pagado": est["total_pagado"],
            "pct_total": pct_total,
        })

    return {
        "id_programa_version_edicion": id_edicion,
        "precio": precio,
        "matricula": matricula,
        "modulos": modulos,
        "alumnos": resultado,
    }


@router.get("/transcript/{id_alumno}")
def transcript_pagos(
    id_alumno: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    es_el_alumno = current_user.profile_type == "alumno" and current_user.id_profile == id_alumno
    if not es_el_alumno:
        if not any(p.codigo == "pagos.ver" for p in current_user.permisos):
            raise HTTPException(status_code=403, detail="No tenés permiso para ver pagos")

    detalles = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_alumno == id_alumno
    ).order_by(DetalleProgramaAlumno.fecha_inscripcion).all()

    pve_ids = {d.id_programa_version_edicion for d in detalles}
    ediciones = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion.in_(pve_ids)
    ).all() if pve_ids else []
    edicion_por_id = {e.id_programa_version_edicion: e for e in ediciones}

    inscripciones = []
    for detalle in detalles:
        edicion = edicion_por_id.get(detalle.id_programa_version_edicion)
        dpm_list = db.query(DetalleProgramaModulo).filter(
            DetalleProgramaModulo.id_programa_version_edicion == detalle.id_programa_version_edicion
        ).order_by(DetalleProgramaModulo.orden).all()
        modulos_nombre = {}
        for dpm in dpm_list:
            mod = db.query(Modulo).filter(Modulo.id_modulo == dpm.id_modulo).first()
            modulos_nombre[dpm.id_detalle_programa_modulo] = mod.nombre_modulo if mod else ""
        orden_por_id = {d.id_detalle_programa_modulo: d.orden for d in dpm_list}

        transacciones = []
        for p, t in _cargar_movimientos(db, [detalle.id_detalle_programa_alumno]):
            if t.id_transaccion not in {x["id_transaccion"] for x in transacciones}:
                transacciones.append({
                    "id_transaccion": t.id_transaccion,
                    "id_orden_pago": t.id_orden_pago,
                    "orden_numero": t.orden_pago.numero if t.orden_pago else None,
                    "fecha_pago": str(t.fecha_pago),
                    "monto_total": float(t.monto_total),
                    "comprobante": t.comprobante,
                    "estado": t.estado,
                    "motivo_anulacion": t.motivo_anulacion,
                    "anulado_fecha": t.anulado_fecha.isoformat() if t.anulado_fecha else None,
                    "anulado_por": _nombre_usuario(db, t.anulado_por_id_usuario),
                    "creado_por": _nombre_usuario(db, t.creado_por_id_usuario),
                    "asignaciones": [],
                })
        trans_by_id = {x["id_transaccion"]: x for x in transacciones}
        for p, t in _cargar_movimientos(db, [detalle.id_detalle_programa_alumno]):
            trans_by_id[t.id_transaccion]["asignaciones"].append({
                "id_pago": p.id_pago,
                "id_detalle_programa_modulo": p.id_detalle_programa_modulo,
                "concepto": p.concepto,
                "orden": orden_por_id.get(p.id_detalle_programa_modulo) or 0,
                "modulo_nombre": modulos_nombre.get(p.id_detalle_programa_modulo),
                "monto": float(p.monto),
            })

        total_pagado = sum(x["monto_total"] for x in transacciones if x["estado"] == "confirmado")

        precio = float(edicion.precio or 0) if edicion else 0.0
        matricula_monto = float(edicion.matricula or 0) if edicion else 0.0
        est = _estado_financiero(db, detalle, dpm_list, precio, matricula_monto)
        esperado_mat = est["matricula_esperado"]
        pagado_mat = est["matricula_pagado"]
        esperado_cuotas = float(sum(est["expecteds"].values()))
        pagado_cuotas = float(sum(v for v in est["pagado_por_dpm"].values()))
        total_esperado = esperado_mat + esperado_cuotas
        pct = round(min(100.0, (est["total_pagado"] / total_esperado) * 100), 1) if total_esperado > 0 else 0
        financiero = {
            "matricula": {
                "esperado": round(esperado_mat, 2),
                "pagado": round(pagado_mat, 2),
                "saldo": round(esperado_mat - pagado_mat, 2),
            },
            "cuotas": {
                "esperado": round(esperado_cuotas, 2),
                "pagado": round(pagado_cuotas, 2),
                "saldo": round(esperado_cuotas - pagado_cuotas, 2),
            },
            "otros_pagado": round(est["otros_pagado"], 2),
            "total_esperado": round(total_esperado, 2),
            "total_pagado": est["total_pagado"],
            "saldo": round(total_esperado - est["total_pagado"], 2),
            "pct": pct,
            "beca_activa": est["beca_activa"],
            "beca_motivo": est["beca_motivo"],
            "descuento_aplicado": _descuento_porcentaje(detalle),
        }

        inscripciones.append({
            "id_detalle_programa_alumno": detalle.id_detalle_programa_alumno,
            "id_programa_version_edicion": detalle.id_programa_version_edicion,
            "programa_nombre": edicion.programa_version.programa.nombre_programa if edicion and edicion.programa_version else None,
            "edicion_numero": edicion.edicion if edicion else None,
            "edicion_anio": edicion.anio if edicion else None,
            "edicion_semestre": edicion.semestre if edicion else None,
            "estado": detalle.estado,
            "es_incorporacion": detalle.es_incorporacion,
            "total_pagado": total_pagado,
            "transacciones": transacciones,
            "financiero": financiero,
        })

    return {"id_alumno": id_alumno, "inscripciones": inscripciones}

