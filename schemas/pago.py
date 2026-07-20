from datetime import datetime, date
from enum import Enum
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class EstadoPagoEnum(str, Enum):
    pendiente = "pendiente"
    confirmado = "confirmado"
    rechazado = "rechazado"


class PagoCreate(BaseModel):
    id_detalle_programa_alumno: int
    monto: Decimal
    fecha_pago: date
    concepto: str
    comprobante_url: str | None = None
    numero_referencia: str | None = None
    estado: EstadoPagoEnum = EstadoPagoEnum.pendiente
    observaciones: str | None = None


class PagoUpdate(BaseModel):
    monto: Decimal | None = None
    fecha_pago: date | None = None
    concepto: str | None = None
    comprobante_url: str | None = None
    numero_referencia: str | None = None
    estado: EstadoPagoEnum | None = None
    observaciones: str | None = None


class PagoResponse(BaseModel):
    id_pago: int
    id_detalle_programa_alumno: int
    monto: Decimal
    fecha_pago: date
    concepto: str
    comprobante_url: str | None
    numero_referencia: str | None
    estado: str
    observaciones: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
