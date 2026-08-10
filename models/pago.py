from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from models.transaccion_pago import TransaccionPago


class Pago(Base):
    __tablename__ = "pagos"

    id_pago = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_transaccion = Column(Integer, ForeignKey("transaccion_pago.id_transaccion"), nullable=False)
    id_detalle_programa_modulo = Column(Integer, ForeignKey("detalle_programa_modulo.id_detalle_programa_modulo"), nullable=True)
    monto = Column(Numeric(10, 2), nullable=False)
    concepto = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    detalle_programa_modulo = relationship("DetalleProgramaModulo")
    transaccion = relationship("TransaccionPago", back_populates="pagos")
