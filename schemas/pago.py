from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class PagoItemResponse(BaseModel):
    id_pago: int
    id_transaccion: int
    id_detalle_programa_modulo: int | None
    monto: Decimal
    concepto: str

    model_config = ConfigDict(from_attributes=True)
