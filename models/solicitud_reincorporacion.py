from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class SolicitudReincorporacion(Base):
    __tablename__ = "solicitud_reincorporacion"

    id_solicitud_reincorporacion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_detalle_programa_alumno = Column(
        Integer,
        ForeignKey("detalle_programa_alumno.id_detalle_programa_alumno"),
        nullable=False,
    )
    estado = Column(String(20), nullable=False, default="pendiente")
    motivo = Column(Text, nullable=True)
    motivo_rechazo = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    detalle_programa_alumno = relationship(
        "DetalleProgramaAlumno",
        foreign_keys=[id_detalle_programa_alumno],
        back_populates="solicitudes_reincorporacion",
    )
