from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class OrdenPago(Base):
    __tablename__ = "orden_pago"

    id_orden_pago = Column(Integer, primary_key=True, index=True, autoincrement=True)
    numero = Column(String(20), unique=True, nullable=False)
    id_detalle_programa_alumno = Column(Integer, ForeignKey("detalle_programa_alumno.id_detalle_programa_alumno"), nullable=False)
    fecha_emision = Column(Date, nullable=False, default=func.current_date())
    monto_total = Column(Numeric(10, 2), nullable=False)
    items = Column(JSONB, nullable=False, default=list)
    estado = Column(String(20), nullable=False, default="emitida")
    motivo_anulacion = Column(Text, nullable=True)
    anulado_por_id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    anulado_fecha = Column(DateTime, nullable=True)
    creado_por_id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    detalle_programa_alumno = relationship("DetalleProgramaAlumno", back_populates="ordenes_pago")
    transaccion = relationship("TransaccionPago", back_populates="orden_pago", uselist=False)
