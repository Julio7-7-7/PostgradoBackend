from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_permiso
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.orden_pago import OrdenPago
from models.pago import Pago
from models.programa_version_edicion import ProgramaVersionEdicion
from models.transaccion_pago import TransaccionPago
from routers.pagos.matriz import _plan_exacto, _serializar_orden
from routers.pagos.transacciones import _serializar_transaccion
from routers._utils import es_alumno_actual, guardar_documento_base64
from schemas.auth import UserResponse
from schemas.orden_pago import OrdenPagoBaja, OrdenPagoEmitir, OrdenPagoPagar, OrdenPagoResponse
from schemas.transaccion_pago import TransaccionPagoResponse

router = APIRouter(
    prefix="/ordenes-pago",
    tags=["Pagos · Órdenes"],
    dependencies=[Depends(get_current_user)]
)


def _generar_numero(db: Session) -> str:
    year = datetime.now().year
    count = db.query(OrdenPago).filter(OrdenPago.numero.like(f"ORD-{year}-%")).count()
    return f"ORD-{year}-{count + 1:04d}"


def _items_desde_plan(plan: list) -> list:
    return [
        {
            "tipo": "matricula" if dpm is None else "cuota",
            "id_detalle_programa_modulo": dpm.id_detalle_programa_modulo if dpm else None,
            "concepto": "Matrícula" if dpm is None else f"Cuota {dpm.orden}",
            "monto": round(m, 2),
        }
        for dpm, m in plan
    ]


@router.post("/preview", status_code=200)
def preview_orden(data: OrdenPagoEmitir, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("pagos.registrar"))):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == data.id_detalle_programa_alumno
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    dpm_list = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == detalle.id_programa_version_edicion
    ).order_by(DetalleProgramaModulo.orden).all()

    edicion = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == detalle.id_programa_version_edicion
    ).first()
    precio = float(edicion.precio or 0) if edicion else 0.0
    matricula = float(edicion.matricula or 0) if edicion else 0.0

    plan, monto_total = _plan_exacto(
        db, detalle, dpm_list, precio, matricula, data.cubre_matricula, data.cantidad_modulos
    )

    return {"items": _items_desde_plan(plan), "monto_total": monto_total}


@router.post("/", status_code=201, response_model=OrdenPagoResponse)
def emitir_orden(data: OrdenPagoEmitir, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == data.id_detalle_programa_alumno
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    es_propia = es_alumno_actual(current_user, detalle.id_alumno, db)
    if not es_propia and not any(p.codigo == "pagos.registrar" for p in current_user.permisos):
        raise HTTPException(status_code=403, detail="No tenés permiso para emitir órdenes de pago")

    dpm_list = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == detalle.id_programa_version_edicion
    ).order_by(DetalleProgramaModulo.orden).all()

    edicion = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == detalle.id_programa_version_edicion
    ).first()
    precio = float(edicion.precio or 0) if edicion else 0.0
    matricula = float(edicion.matricula or 0) if edicion else 0.0

    plan, monto_total = _plan_exacto(
        db, detalle, dpm_list, precio, matricula, data.cubre_matricula, data.cantidad_modulos
    )

    activa = db.query(OrdenPago).filter(
        OrdenPago.id_detalle_programa_alumno == detalle.id_detalle_programa_alumno,
        OrdenPago.estado == "emitida",
    ).first()
    if activa:
        raise HTTPException(
            status_code=400,
            detail=f"El alumno ya tiene una orden emitida sin cobrar ({activa.numero})",
        )

    orden = OrdenPago(
        numero=_generar_numero(db),
        id_detalle_programa_alumno=detalle.id_detalle_programa_alumno,
        fecha_emision=data.fecha_emision or date.today(),
        monto_total=monto_total,
        items=_items_desde_plan(plan),
        estado="emitida",
        creado_por_id_usuario=current_user.id_usuario,
    )
    db.add(orden)
    db.flush()
    db.commit()
    db.refresh(orden)
    return _serializar_orden(db, orden)


@router.get("/por-edicion/{id_edicion}")
def ordenes_por_edicion(
    id_edicion: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver"))
):
    edicion = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id_edicion
    ).first()
    if not edicion:
        raise HTTPException(status_code=404, detail="Edición no encontrada")

    dpa_ids = [
        d.id_detalle_programa_alumno
        for d in db.query(DetalleProgramaAlumno.id_detalle_programa_alumno).filter(
            DetalleProgramaAlumno.id_programa_version_edicion == id_edicion
        ).all()
    ]
    if not dpa_ids:
        return []

    ordenes = db.query(OrdenPago).filter(
        OrdenPago.id_detalle_programa_alumno.in_(dpa_ids)
    ).order_by(OrdenPago.created_at.desc()).all()

    return [_serializar_orden(db, o) for o in ordenes]


@router.get("/dpa/{id_dpa}", response_model=list[OrdenPagoResponse])
def ordenes_por_dpa(
    id_dpa: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver"))
):
    ordenes = db.query(OrdenPago).filter(
        OrdenPago.id_detalle_programa_alumno == id_dpa
    ).order_by(OrdenPago.created_at.desc()).all()
    return [_serializar_orden(db, o) for o in ordenes]


@router.get("/mis-ordenes/{id_dpa}", response_model=list[OrdenPagoResponse])
def mis_ordenes_por_dpa(
    id_dpa: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id_dpa
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    if not es_alumno_actual(current_user, detalle.id_alumno, db):
        raise HTTPException(status_code=403, detail="No tenés acceso a esta inscripción")
    ordenes = db.query(OrdenPago).filter(
        OrdenPago.id_detalle_programa_alumno == id_dpa
    ).order_by(OrdenPago.created_at.desc()).all()
    return [_serializar_orden(db, o) for o in ordenes]


@router.get("/{id}", response_model=OrdenPagoResponse)
def obtener_orden(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver"))
):
    orden = db.query(OrdenPago).filter(OrdenPago.id_orden_pago == id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de pago no encontrada")
    return _serializar_orden(db, orden)


@router.patch("/{id}/anular", response_model=OrdenPagoResponse)
def anular_orden(
    id: int,
    data: OrdenPagoBaja,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.anular"))
):
    orden = db.query(OrdenPago).filter(OrdenPago.id_orden_pago == id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de pago no encontrada")
    if orden.estado == "pagada":
        raise HTTPException(status_code=400, detail="La orden ya fue cobrada; anulá la transacción, no la orden")
    if orden.estado == "anulada":
        raise HTTPException(status_code=400, detail="La orden ya está anulada")

    motivo = (data.motivo_anulacion or "").strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="El motivo de la anulación es obligatorio")

    orden.estado = "anulada"
    orden.motivo_anulacion = motivo
    orden.anulado_por_id_usuario = current_user.id_usuario
    orden.anulado_fecha = datetime.utcnow()

    db.flush()
    db.commit()
    db.refresh(orden)
    return _serializar_orden(db, orden)


@router.post("/{id}/pagar", status_code=201, response_model=TransaccionPagoResponse)
def pagar_orden(
    id: int,
    data: OrdenPagoPagar,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.registrar"))
):
    orden = db.query(OrdenPago).filter(OrdenPago.id_orden_pago == id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de pago no encontrada")
    if orden.estado == "pagada":
        raise HTTPException(status_code=400, detail="La orden ya fue cobrada")
    if orden.estado == "anulada":
        raise HTTPException(status_code=400, detail="La orden está anulada")

    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == orden.id_detalle_programa_alumno
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    if es_alumno_actual(current_user, detalle.id_alumno, db):
        raise HTTPException(status_code=403, detail="No podés registrar pagos para tu propia inscripción")

    comprobante = None
    if data.comprobante:
        comprobante = guardar_documento_base64(data.comprobante, media_subdir="pagos")

    transaccion = TransaccionPago(
        id_detalle_programa_alumno=orden.id_detalle_programa_alumno,
        id_orden_pago=orden.id_orden_pago,
        monto_total=float(orden.monto_total),
        fecha_pago=data.fecha_pago,
        comprobante=comprobante,
        estado="confirmado",
        creado_por_id_usuario=current_user.id_usuario,
    )
    db.add(transaccion)
    db.flush()

    for item in orden.items:
        db.add(Pago(
            id_transaccion=transaccion.id_transaccion,
            id_detalle_programa_modulo=item.get("id_detalle_programa_modulo"),
            monto=round(float(item["monto"]), 2),
            concepto=item["concepto"],
        ))

    orden.estado = "pagada"

    db.commit()
    db.refresh(transaccion)
    return _serializar_transaccion(transaccion)
