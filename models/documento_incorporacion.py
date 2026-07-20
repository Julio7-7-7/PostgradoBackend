from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class DocumentoIncorporacion(Base):
    __tablename__ = "documento_incorporacion"

    id_documento_incorporacion = Column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    id_detalle_programa_alumno = Column(
        Integer,
        ForeignKey("detalle_programa_alumno.id_detalle_programa_alumno"),
        nullable=False,
    )
    tipo_documento = Column(String(100), nullable=False)
    estado = Column(String(20), nullable=False, default="pendiente")
    url_documento = Column(String(500), nullable=True)
    observaciones = Column(Text, nullable=True)
    fecha_entrega = Column(Date, nullable=True)
    fecha_revision = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    detalle_programa_alumno = relationship(
        "DetalleProgramaAlumno", back_populates="documentos_incorporacion"
    )
