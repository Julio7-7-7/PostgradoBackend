from sqlalchemy import Column, Integer, Date, DateTime, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Nota(Base):
    __tablename__ = "notas"
    __table_args__ = (
        UniqueConstraint('id_detalle_programa_alumno', 'id_detalle_programa_modulo', name='uq_nota_alumno_modulo'),
    )

    id_nota = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_detalle_programa_alumno = Column(Integer, ForeignKey("detalle_programa_alumno.id_detalle_programa_alumno"), nullable=False)
    id_detalle_programa_modulo = Column(Integer, ForeignKey("detalle_programa_modulo.id_detalle_programa_modulo"), nullable=False)
    nota = Column(Numeric(5, 2), nullable=False)
    fecha = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    detalle_programa_alumno = relationship("DetalleProgramaAlumno", back_populates="notas")
    detalle_programa_modulo = relationship("DetalleProgramaModulo")
