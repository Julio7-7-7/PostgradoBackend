import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_permiso
from models.alumno import Alumno
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.historial_inscripcion import HistorialInscripcion
from models.modulo import Modulo
from models.nota import Nota
from models.pago import Pago
from models.programa_version_edicion import ProgramaVersionEdicion
from schemas.auth import UserResponse
from schemas.enums import clasificar_nota
from schemas.pago import PagoCreate, PagoResponse, PagoUpdate
from routers.utils import eliminar_foto, es_alumno_actual

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

    pagos = db.query(Pago).filter(
        Pago.id_detalle_programa_alumno == detalle.id_detalle_programa_alumno
    ).all()

    origen_ids = _origenes_transitivos(db, detalle.id_detalle_programa_alumno)
    pagos_origen: list[Pago] = []
    origin_dpm_por_id: dict[int, DetalleProgramaModulo] = {}
    origin_edicion_por_dpa: dict[int, dict] = {}
    if origen_ids:
        pagos_origen = db.query(Pago).filter(Pago.id_detalle_programa_alumno.in_(origen_ids)).all()
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
        origin_dpm_ids = {p.id_detalle_programa_modulo for p in pagos_origen if p.id_detalle_programa_modulo}
        origin_dpms = db.query(DetalleProgramaModulo).filter(
            DetalleProgramaModulo.id_detalle_programa_modulo.in_(origin_dpm_ids)
        ).all() if origin_dpm_ids else []
        origin_dpm_por_id = {d.id_detalle_programa_modulo: d for d in origin_dpms}

    pagado_por_dpm: dict[int, float] = {d.id_detalle_programa_modulo: 0.0 for d in dpm_list}
    cuota_pagos: dict[int, list] = {d.id_detalle_programa_modulo: [] for d in dpm_list}
    matricula_pagos: list = []
    otros_pagos: list = []
    total_pagado = 0.0

    def _marcar_origen(p: Pago, es_origen: bool):
        if not es_origen:
            return None
        return origin_edicion_por_dpa.get(p.id_detalle_programa_alumno)

    def _entry(p: Pago, es_origen: bool) -> dict:
        return {
            "id_pago": p.id_pago,
            "monto": float(p.monto),
            "fecha_pago": str(p.fecha_pago),
            "numero_referencia": p.numero_referencia,
            "estado": p.estado,
            "origen": _marcar_origen(p, es_origen),
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

    def _aplicar(p: Pago, es_origen: bool):
        nonlocal total_pagado
        target = _target_de(p, es_origen)
        if target == "matricula":
            matricula_pagos.append(_entry(p, es_origen))
        elif target not in cuota_pagos:
            otros_pagos.append(_entry(p, es_origen))
        else:
            cuota_pagos[target].append(_entry(p, es_origen))
        if p.estado != "confirmado":
            return
        if target == "matricula":
            total_pagado += float(p.monto)
        elif target not in cuota_pagos:
            total_pagado += float(p.monto)
        else:
            pagado_por_dpm[target] += float(p.monto)
            total_pagado += float(p.monto)

    for p in pagos:
        _aplicar(p, False)
    for p in pagos_origen:
        _aplicar(p, True)

    matricula_pagado = sum(float(p.monto) for p in pagos + pagos_origen
                           if p.estado == "confirmado" and p.id_detalle_programa_modulo is None)
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
    est = _estado_financiero(db, detalle, dpm_list, precio, matricula)
    asignaciones: list[tuple] = []
    restante = monto_total
    if target_dpm_id is None:
        resto_mat = max(0.0, est["matricula_esperado"] - est["matricula_pagado"])
        if restante > 0 and resto_mat > 0:
            m = min(resto_mat, restante)
            asignaciones.append((None, m))
            restante -= m
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
    return PagoResponse.model_validate(p).model_dump(mode="json")


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


@router.get("/mis-pagos/{id_detalle}")
def mis_pagos(
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

    pagos = db.query(Pago).filter(
        Pago.id_detalle_programa_alumno == id_detalle
    ).order_by(Pago.fecha_pago.desc()).all()

    total_pagado = sum(float(p.monto) for p in pagos if p.estado == "confirmado")

    return {
        "pagos": pagos,
        "total_pagado": total_pagado,
    }


@router.post("/", status_code=201)
def crear_pago(data: PagoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("pagos.registrar"))):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == data.id_detalle_programa_alumno
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    monto_total = float(data.monto)
    if monto_total <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")

    if es_alumno_actual(current_user, detalle.id_alumno, db):
        raise HTTPException(status_code=403, detail="No podés registrar pagos para tu propia inscripción")

    dpm_list = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == detalle.id_programa_version_edicion
    ).order_by(DetalleProgramaModulo.orden).all()

    if data.id_detalle_programa_modulo is not None:
        if data.id_detalle_programa_modulo not in {d.id_detalle_programa_modulo for d in dpm_list}:
            raise HTTPException(status_code=400, detail="El módulo no pertenece a la edición de la inscripción")

    edicion = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == detalle.id_programa_version_edicion
    ).first()
    precio = float(edicion.precio or 0) if edicion else 0.0
    matricula = float(edicion.matricula or 0) if edicion else 0.0

    plan = _planificar_cobro(db, detalle, dpm_list, precio, data.id_detalle_programa_modulo, monto_total, matricula)

    estado = data.estado.value if hasattr(data.estado, "value") else data.estado

    creados = []
    for dpm, monto_parcial in plan:
        pago = Pago(
            id_detalle_programa_alumno=data.id_detalle_programa_alumno,
            id_detalle_programa_modulo=dpm.id_detalle_programa_modulo if dpm else None,
            monto=round(monto_parcial, 2),
            fecha_pago=data.fecha_pago,
            concepto="Matrícula" if dpm is None else f"Cuota {dpm.orden}",
            comprobante_url=data.comprobante_url,
            numero_referencia=data.numero_referencia,
            estado=estado,
            observaciones=data.observaciones,
        )
        db.add(pago)
        creados.append(pago)

    db.flush()
    db.commit()
    for p in creados:
        db.refresh(p)

    return {"pagos": [_serializar_pago(p) for p in creados]}


@router.patch("/{id}", response_model=PagoResponse)
def editar_pago(
    id: int,
    data: PagoUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.registrar"))
):
    pago = db.query(Pago).filter(Pago.id_pago == id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    detalle_pago = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == pago.id_detalle_programa_alumno
    ).first()
    if detalle_pago and es_alumno_actual(current_user, detalle_pago.id_alumno, db):
        raise HTTPException(status_code=403, detail="No podés modificar pagos de tu propia inscripción")

    if data.monto is not None and float(data.monto) <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")

    if data.id_detalle_programa_modulo is not None and detalle_pago:
        existe = db.query(DetalleProgramaModulo).filter(
            DetalleProgramaModulo.id_detalle_programa_modulo == data.id_detalle_programa_modulo,
            DetalleProgramaModulo.id_programa_version_edicion == detalle_pago.id_programa_version_edicion,
        ).first()
        if not existe:
            raise HTTPException(status_code=400, detail="El módulo no pertenece a la edición de la inscripción")

    if data.comprobante_url and pago.comprobante_url:
        eliminar_foto(pago.comprobante_url)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(pago, key, value)
    db.flush()
    db.commit()
    db.refresh(pago)
    return pago


@router.get("/{id}", response_model=PagoResponse)
def obtener_pago(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver"))
):
    pago = db.query(Pago).filter(Pago.id_pago == id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return pago
