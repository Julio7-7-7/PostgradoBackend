from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class HistorialModulo(Base):
    __tablename__ = "historial_modulo"

    id_historial = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_detalle_programa_modulo = Column(Integer, ForeignKey("detalle_programa_modulo.id_detalle_programa_modulo"), nullable=False)
    estado_anterior = Column(String(20), nullable=True)
    estado_nuevo = Column(String(20), nullable=True)
    motivo = Column(String(500), nullable=False)
    fecha_inicio_original = Column(Date, nullable=True)
    fecha_fin_original = Column(Date, nullable=True)
    fecha_inicio_nuevo = Column(Date, nullable=True)
    fecha_fin_nuevo = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    detalle_programa_modulo = relationship("DetalleProgramaModulo", back_populates="historial")
