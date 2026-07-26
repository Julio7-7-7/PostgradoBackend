from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class SolicitudIncorporacion(Base):
    __tablename__ = "solicitud_incorporacion"

    id_solicitud = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_detalle_programa_alumno = Column(
        Integer,
        ForeignKey("detalle_programa_alumno.id_detalle_programa_alumno"),
        nullable=True,
    )
    id_programa_version_edicion = Column(
        Integer,
        ForeignKey("programa_version_edicion.id_programa_version_edicion"),
        nullable=True,
    )
    estado = Column(String(20), nullable=False, default="pendiente")
    observaciones = Column(Text, nullable=True)
    fecha_revision = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    detalle_programa_alumno = relationship(
        "DetalleProgramaAlumno", back_populates="solicitudes_incorporacion"
    )
    programa_version_edicion = relationship(
        "ProgramaVersionEdicion", back_populates="solicitudes_incorporacion"
    )
    documentos = relationship("SolicitudDocumento", back_populates="solicitud")


class SolicitudDocumento(Base):
    __tablename__ = "solicitud_documento"

    id_solicitud_documento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_solicitud = Column(Integer, ForeignKey("solicitud_incorporacion.id_solicitud"), nullable=False)
    id_requisito = Column(Integer, ForeignKey("requisitos.id_requisito"), nullable=False)
    url_documento = Column(String(500), nullable=False)
    estado = Column(String(20), nullable=False, default="pendiente")
    fecha_entrega = Column(DateTime, server_default=func.now(), nullable=False)

    solicitud = relationship("SolicitudIncorporacion", back_populates="documentos")
    requisito = relationship("Requisito")
