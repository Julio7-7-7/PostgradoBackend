from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class AvanceModulo(Base):
    __tablename__ = "avance_modulo"
    __table_args__ = (
        UniqueConstraint(
            "id_detalle_programa_alumno",
            "id_detalle_programa_modulo",
            name="uq_avance_alumno_modulo",
        ),
    )

    id_avance = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_detalle_programa_alumno = Column(
        Integer,
        ForeignKey("detalle_programa_alumno.id_detalle_programa_alumno"),
        nullable=False,
    )
    id_detalle_programa_modulo = Column(
        Integer,
        ForeignKey("detalle_programa_modulo.id_detalle_programa_modulo"),
        nullable=False,
    )
    completado_en_edicion = Column(
        Integer,
        ForeignKey("programa_version_edicion.id_programa_version_edicion"),
        nullable=False,
    )
    fecha_completion = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    detalle_programa_alumno = relationship(
        "DetalleProgramaAlumno", back_populates="avances"
    )
    detalle_programa_modulo = relationship("DetalleProgramaModulo")
    edicion = relationship("ProgramaVersionEdicion")
