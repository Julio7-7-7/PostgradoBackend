from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class TransaccionPago(Base):
    __tablename__ = "transaccion_pago"

    id_transaccion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_detalle_programa_alumno = Column(Integer, ForeignKey("detalle_programa_alumno.id_detalle_programa_alumno"), nullable=False)
    monto_total = Column(Numeric(10, 2), nullable=False)
    fecha_pago = Column(Date, nullable=False)
    comprobante = Column(String(500), nullable=True)
    estado = Column(String(20), nullable=False, default="confirmado")
    motivo_anulacion = Column(Text, nullable=True)
    anulado_por_id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    anulado_fecha = Column(DateTime, nullable=True)
    creado_por_id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    detalle_programa_alumno = relationship("DetalleProgramaAlumno", back_populates="transacciones_pago")
    pagos = relationship("Pago", back_populates="transaccion")
