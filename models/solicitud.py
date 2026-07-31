from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Solicitud(Base):
    __tablename__ = "solicitud"

    id_solicitud = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_tipo_solicitud = Column(
        Integer, ForeignKey("tipo_solicitud.id_tipo_solicitud"), nullable=False
    )
    id_alumno = Column(Integer, ForeignKey("alumnos.id_alumno"), nullable=False)
    id_detalle_origen = Column(
        Integer,
        ForeignKey("detalle_programa_alumno.id_detalle_programa_alumno"),
        nullable=True,
    )
    estado = Column(String(20), nullable=False, default="pendiente")
    motivo = Column(Text, nullable=True)
    motivo_rechazo = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tipo = relationship("TipoSolicitud", back_populates="solicitudes")
    alumno = relationship("Alumno", backref="solicitudes")
    detalle_origen = relationship(
        "DetalleProgramaAlumno",
        foreign_keys=[id_detalle_origen],
        backref="solicitudes_origen",
    )
    incorporacion = relationship("SolicitudIncorporacion", uselist=False, back_populates="solicitud")
    migracion = relationship("SolicitudMigracion", uselist=False, back_populates="solicitud")
    documentos = relationship("DocumentoSolicitud", back_populates="solicitud", cascade="all, delete-orphan")
