from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Nota(Base):
    __tablename__ = "notas"

    id_nota = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_detalle_programa_alumno = Column(Integer, ForeignKey("detalle_programa_alumno.id_detalle_programa_alumno"), nullable=False)
    id_detalle_programa_modulo = Column(Integer, ForeignKey("detalle_programa_modulo.id_detalle_programa_modulo"), nullable=False)
    id_programa_version_edicion = Column(Integer, ForeignKey("programa_version_edicion.id_programa_version_edicion"), nullable=True)
    nota = Column(Numeric(5, 2), nullable=False)
    tipo = Column(String(50), nullable=False, default="final")
    fecha = Column(Date, nullable=False)
    observaciones = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    detalle_programa_alumno = relationship("DetalleProgramaAlumno", back_populates="notas")
    detalle_programa_modulo = relationship("DetalleProgramaModulo")
