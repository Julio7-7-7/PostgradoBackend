from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class HistorialInscripcion(Base):
    __tablename__ = "historial_inscripcion"

    id_historial = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_detalle_origen = Column(
        Integer,
        ForeignKey("detalle_programa_alumno.id_detalle_programa_alumno"),
        nullable=False,
    )
    id_detalle_destino = Column(
        Integer,
        ForeignKey("detalle_programa_alumno.id_detalle_programa_alumno"),
        nullable=False,
    )
    id_solicitud = Column(
        Integer,
        ForeignKey("solicitud.id_solicitud"),
        nullable=False,
    )
    tipo_movimiento = Column(String(20), nullable=False)
    motivo = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    origen = relationship(
        "DetalleProgramaAlumno",
        foreign_keys=[id_detalle_origen],
        back_populates="historial_origen",
    )
    destino = relationship(
        "DetalleProgramaAlumno",
        foreign_keys=[id_detalle_destino],
        back_populates="historial_destino",
    )
    solicitud = relationship(
        "Solicitud",
        foreign_keys=[id_solicitud],
        backref="historiales",
    )
