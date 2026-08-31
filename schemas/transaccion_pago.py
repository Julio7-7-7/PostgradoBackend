from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field

from schemas.pago import PagoItemResponse


class TransaccionPagoBaja(BaseModel):
    motivo_anulacion: str = Field(..., min_length=1)


class TransaccionPagoResponse(BaseModel):
    id_transaccion: int
    id_detalle_programa_alumno: int
    id_orden_pago: int | None
    orden_numero: str | None = None
    monto_total: float
    fecha_pago: date
    comprobante: str | None
    codigo_boleta: str | None = None
    estado: str
    motivo_anulacion: str | None
    anulado_por_id_usuario: int | None
    anulado_fecha: datetime | None
    creado_por_id_usuario: int | None
    created_at: datetime
    updated_at: datetime
    pagos: list[PagoItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
