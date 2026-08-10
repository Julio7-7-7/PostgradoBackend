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
from models.pago import Pago
from models.programa_version_edicion import ProgramaVersionEdicion
from models.transaccion_pago import TransaccionPago
from models.usuario import Usuario
from schemas.auth import UserResponse
from schemas.enums import clasificar_nota
from schemas.transaccion_pago import TransaccionPagoCreate

router = APIRouter(
    prefix="/pagos",
    tags=["Pagos"],
    dependencies=[Depends(get_current_user)]
)

BECA_PERDIDA_CALIFICACIONES = {"insuficiente", "abandono"}


def _descuento_porcentaje(detalle) -> float:
    return max(0.0, min(100.0, float(detalle.descuento_aplicado or 0)))


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
                    f" — las cuotas restantes pasan a precio pleno"
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


def _planificar_cobro(db: Session, detalle, dpm_list: list, precio: float, target_dpm_id, monto_total: float, matricula: float = 0.0):
    """Reparte el monto: la matrícula siempre se cobra primero, luego las cuotas desde el target."""
    est = _estado_financiero(db, detalle, dpm_list, precio, matricula)
    asignaciones: list[tuple] = []
    restante = monto_total

    resto_mat = max(0.0, est["matricula_esperado"] - est["matricula_pagado"])
    if restante > 0 and resto_mat > 0:
        m = min(resto_mat, restante)
        asignaciones.append((None, m))
        restante -= m

    if target_dpm_id is None:
        start = 0
    else:
        start = next(
            (i for i, d in enumerate(dpm_list) if d.id_detalle_programa_modulo == target_dpm_id),
            0,
        )
    for i in range(start, len(dpm_list)):
        if restante <= 0:
            break
        dpm = dpm_list[i]
        resto = max(0.0, est["expecteds"].get(dpm.id_detalle_programa_modulo, 0.0) - est["pagado_por_dpm"].get(dpm.id_detalle_programa_modulo, 0.0))
        if resto <= 0:
            continue
        m = min(resto, restante)
        asignaciones.append((dpm, m))
        restante -= m
    if restante > 0:
        if asignaciones:
            dpm, m = asignaciones[-1]
            asignaciones[-1] = (dpm, m + restante)
        else:
            asignaciones.append((None, restante))
    return asignaciones


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

    resultado = []
    for detalle in detalles:
        alumno = db.query(Alumno).filter(Alumno.id_alumno == detalle.id_alumno).first()
        est = _estado_financiero(db, detalle, dpm_list, precio, matricula)

        total_esperado = round(est["matricula_esperado"] + est["total_esperado_cuotas"], 2)
        pct_total = round(est["total_pagado"] / total_esperado * 100, 1) if total_esperado else 0.0

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
                "pct": round(pagado / esperado * 100, 1) if esperado else 0.0,
                "pagos": est["cuota_pagos"].get(dpm.id_detalle_programa_modulo, []),
            })

        matricula_pagado = round(est["matricula_pagado"], 2)
        matricula_esperado = est["matricula_esperado"]

        resultado.append({
            "id_detalle_programa_alumno": detalle.id_detalle_programa_alumno,
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
                "pct": round(matricula_pagado / matricula_esperado * 100, 1) if matricula_esperado else 0.0,
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
        pct = round((est["total_pagado"] / total_esperado) * 100, 1) if total_esperado > 0 else 0
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


@router.post("/preview", status_code=200)
def preview_cobro(data: TransaccionPagoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("pagos.registrar"))):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == data.id_detalle_programa_alumno
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    monto_total = float(data.monto)
    if monto_total <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")

    dpm_list = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == detalle.id_programa_version_edicion
    ).order_by(DetalleProgramaModulo.orden).all()

    edicion = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == detalle.id_programa_version_edicion
    ).first()
    precio = float(edicion.precio or 0) if edicion else 0.0
    matricula = float(edicion.matricula or 0) if edicion else 0.0

    plan = _planificar_cobro(db, detalle, dpm_list, precio, data.id_detalle_programa_modulo, monto_total, matricula)

    return {
        "asignaciones": [
            {
                "tipo": "matricula" if dpm is None else "cuota",
                "id_detalle_programa_modulo": dpm.id_detalle_programa_modulo if dpm else None,
                "concepto": "Matrícula" if dpm is None else f"Cuota {dpm.orden}",
                "monto": round(m, 2),
            }
            for dpm, m in plan
        ]
    }

