from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class DetalleProgramaModulo(Base):
    __tablename__ = "detalle_programa_modulo"
    __table_args__ = (
        UniqueConstraint('id_programa_version_edicion', 'orden', name='uq_detalle_orden_edicion'),
    )

    id_detalle_programa_modulo = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_programa_version_edicion = Column(Integer, ForeignKey("programa_version_edicion.id_programa_version_edicion"), nullable=False)
    id_modulo = Column(Integer, ForeignKey("modulos.id_modulo"), nullable=False)
    id_docente = Column(Integer, ForeignKey("docentes.id_docente"), nullable=True)
    id_modalidad = Column(Integer, ForeignKey("modalidades.id_modalidad"), nullable=True)
    orden = Column(Integer, nullable=False)
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    estado = Column(String(20), nullable=False, default="programado")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    programa_version_edicion = relationship("ProgramaVersionEdicion", back_populates="detalles_modulo")
    modulo = relationship("Modulo", back_populates="detalles")
    docente = relationship("Docente", back_populates="detalles")
    modalidad = relationship("Modalidad", back_populates="detalles_modulo")
    historial = relationship("HistorialModulo", back_populates="detalle_programa_modulo")
    horarios = relationship("Horario", back_populates="detalle_programa_modulo")