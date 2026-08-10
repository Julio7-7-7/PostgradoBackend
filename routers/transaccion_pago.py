from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_permiso
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.pago import Pago
from models.programa_version_edicion import ProgramaVersionEdicion
from models.transaccion_pago import TransaccionPago
from routers.pago import _cargar_movimientos, _planificar_cobro, _serializar_pago
from routers.utils import es_alumno_actual, guardar_documento_base64
from schemas.auth import UserResponse
from schemas.transaccion_pago import TransaccionPagoBaja, TransaccionPagoCreate, TransaccionPagoResponse

router = APIRouter(
    prefix="/pagos",
    tags=["Pagos · Transacciones"],
    dependencies=[Depends(get_current_user)]
)


def _serializar_transaccion(t: TransaccionPago) -> dict:
    return {
        "id_transaccion": t.id_transaccion,
        "id_detalle_programa_alumno": t.id_detalle_programa_alumno,
        "monto_total": float(t.monto_total),
        "fecha_pago": str(t.fecha_pago),
        "comprobante": t.comprobante,
        "estado": t.estado,
        "motivo_anulacion": t.motivo_anulacion,
        "anulado_por_id_usuario": t.anulado_por_id_usuario,
        "anulado_fecha": t.anulado_fecha.isoformat() if t.anulado_fecha else None,
        "creado_por_id_usuario": t.creado_por_id_usuario,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        "pagos": [_serializar_pago(p) for p in t.pagos],
    }


@router.post("/", status_code=201, response_model=TransaccionPagoResponse)
def crear_pago(data: TransaccionPagoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("pagos.registrar"))):
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

    comprobante = None
    if data.comprobante:
        comprobante = guardar_documento_base64(data.comprobante, media_subdir="pagos")

    transaccion = TransaccionPago(
        id_detalle_programa_alumno=detalle.id_detalle_programa_alumno,
        monto_total=round(monto_total, 2),
        fecha_pago=data.fecha_pago,
        comprobante=comprobante,
        estado="confirmado",
        creado_por_id_usuario=current_user.id_usuario,
    )
    db.add(transaccion)
    db.flush()

    for dpm, monto_parcial in plan:
        pago = Pago(
            id_transaccion=transaccion.id_transaccion,
            id_detalle_programa_modulo=dpm.id_detalle_programa_modulo if dpm else None,
            monto=round(monto_parcial, 2),
            concepto="Matrícula" if dpm is None else f"Cuota {dpm.orden}",
        )
        db.add(pago)

    db.commit()
    db.refresh(transaccion)
    return transaccion


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
    return transaccion


@router.get("/{id}", response_model=TransaccionPagoResponse)
def obtener_transaccion(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver"))
):
    transaccion = db.query(TransaccionPago).filter(TransaccionPago.id_transaccion == id).first()
    if not transaccion:
        raise HTTPException(status_code=404, detail="Transacción de pago no encontrada")
    return transaccion
