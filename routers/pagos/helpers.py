from sqlalchemy.orm import Session

from models.detalle_programa_modulo import DetalleProgramaModulo
from models.programa_version_edicion import ProgramaVersionEdicion
from routers.pagos.matriz import _estado_financiero


def saldo_pendiente_dpas(db: Session, id_edicion: int, dpas: list) -> dict:
    """Saldo pendiente (monto esperado - pagado confirmado) por DPA.

    Con un saldo > 0 el alumno NO tiene pagos completos, aunque no tenga
    ninguna orden emitida (corrige el bug de "sin órdenes = pago completo").
    """
    if not dpas:
        return {}

    edicion = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id_edicion
    ).first()
    precio = float(edicion.precio or 0) if edicion else 0.0
    matricula = float(edicion.matricula or 0) if edicion else 0.0

    dpm_list = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == id_edicion
    ).order_by(DetalleProgramaModulo.orden).all()

    saldos: dict = {}
    for d in dpas:
        est = _estado_financiero(db, d, dpm_list, precio, matricula)
        total_esperado = est["matricula_esperado"] + est["total_esperado_cuotas"]
        saldo = round(total_esperado - est["total_pagado"], 2)
        saldos[d.id_detalle_programa_alumno] = saldo
    return saldos
