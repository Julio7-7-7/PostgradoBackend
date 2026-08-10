from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from schemas.pago import PagoItemResponse


class TransaccionPagoCreate(BaseModel):
    id_detalle_programa_alumno: int
    id_detalle_programa_modulo: int | None = None
    monto: Decimal
    fecha_pago: date
    comprobante: str | None = None


class TransaccionPagoBaja(BaseModel):
    motivo_anulacion: str = Field(..., min_length=1)


class TransaccionPagoResponse(BaseModel):
    id_transaccion: int
    id_detalle_programa_alumno: int
    monto_total: Decimal
    fecha_pago: date
    comprobante: str | None
    estado: str
    motivo_anulacion: str | None
    anulado_por_id_usuario: int | None
    anulado_fecha: datetime | None
    creado_por_id_usuario: int | None
    created_at: datetime
    updated_at: datetime
    pagos: list[PagoItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
