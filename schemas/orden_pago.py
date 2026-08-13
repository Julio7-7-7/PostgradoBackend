from datetime import date, datetime
from pydantic import BaseModel, Field


class OrdenPagoItem(BaseModel):
    tipo: str  # matricula | cuota
    id_detalle_programa_modulo: int | None
    concepto: str
    monto: float


class OrdenPagoEmitir(BaseModel):
    id_detalle_programa_alumno: int
    cubre_matricula: bool = False
    cantidad_modulos: int = 0
    fecha_emision: date | None = None


class OrdenPagoPreviewResponse(BaseModel):
    items: list[OrdenPagoItem]
    monto_total: float


class OrdenPagoPagar(BaseModel):
    fecha_pago: date
    comprobante: str | None = None


class OrdenPagoBaja(BaseModel):
    motivo_anulacion: str = Field(..., min_length=1)


class OrdenPagoAlumno(BaseModel):
    id_alumno: int
    nombre: str
    apellido: str
    ci: str | None


class OrdenPagoEdicion(BaseModel):
    programa: str | None
    edicion: int | None
    anio: int | None
    semestre: int | None


class OrdenPagoResponse(BaseModel):
    id_orden_pago: int
    numero: str
    id_detalle_programa_alumno: int
    fecha_emision: date
    monto_total: float
    items: list[OrdenPagoItem]
    estado: str
    motivo_anulacion: str | None
    anulado_por_id_usuario: int | None
    anulado_fecha: datetime | None
    creado_por_id_usuario: int | None
    created_at: datetime
    updated_at: datetime
    id_transaccion: int | None
    alumno: OrdenPagoAlumno | None
    edicion: OrdenPagoEdicion | None
