from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_permiso
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.transaccion_pago import TransaccionPago
from routers.pagos.matriz import _cargar_movimientos, _serializar_pago
from schemas.auth import UserResponse
from schemas.transaccion_pago import TransaccionPagoBaja, TransaccionPagoResponse

router = APIRouter(
    prefix="/pagos",
    tags=["Pagos · Transacciones"],
    dependencies=[Depends(get_current_user)]
)


def _serializar_transaccion(t: TransaccionPago) -> dict:
    return {
        "id_transaccion": t.id_transaccion,
        "id_detalle_programa_alumno": t.id_detalle_programa_alumno,
        "id_orden_pago": t.id_orden_pago,
        "orden_numero": t.orden_pago.numero if t.orden_pago else None,
        "monto_total": float(t.monto_total),
        "fecha_pago": str(t.fecha_pago),
        "comprobante": t.comprobante,
        "codigo_boleta": t.codigo_boleta,
        "estado": t.estado,
        "motivo_anulacion": t.motivo_anulacion,
        "anulado_por_id_usuario": t.anulado_por_id_usuario,
        "anulado_fecha": t.anulado_fecha.isoformat() if t.anulado_fecha else None,
        "creado_por_id_usuario": t.creado_por_id_usuario,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        "pagos": [_serializar_pago(p) for p in t.pagos],
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

    movimientos = _cargar_movimientos(db, [id_detalle])
    total_pagado = sum(float(p.monto) for p, t in movimientos if t.estado == "confirmado")

    transacciones = {}
    for p, t in movimientos:
        transacciones[t.id_transaccion] = t
    lista = sorted(transacciones.values(), key=lambda t: t.fecha_pago, reverse=True)

    return {
        "transacciones": [_serializar_transaccion(t) for t in lista],
        "total_pagado": total_pagado,
    }


@router.patch("/transacciones/{id}/anular", response_model=TransaccionPagoResponse)
def anular_transaccion(
    id: int,
    data: TransaccionPagoBaja,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.anular"))
):
    transaccion = db.query(TransaccionPago).filter(TransaccionPago.id_transaccion == id).first()
    if not transaccion:
        raise HTTPException(status_code=404, detail="Transacción de pago no encontrada")
    if transaccion.estado == "anulado":
        raise HTTPException(status_code=400, detail="La transacción ya está anulada")

    motivo = (data.motivo_anulacion or "").strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="El motivo de la anulación es obligatorio")

    transaccion.estado = "anulado"
    transaccion.motivo_anulacion = motivo
    transaccion.anulado_por_id_usuario = current_user.id_usuario
    transaccion.anulado_fecha = datetime.utcnow()

    db.flush()
    db.commit()
    db.refresh(transaccion)
    return _serializar_transaccion(transaccion)


@router.get("/{id}", response_model=TransaccionPagoResponse)
def obtener_transaccion(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver"))
):
    transaccion = db.query(TransaccionPago).filter(TransaccionPago.id_transaccion == id).first()
    if not transaccion:
        raise HTTPException(status_code=404, detail="Transacción de pago no encontrada")
    return _serializar_transaccion(transaccion)
