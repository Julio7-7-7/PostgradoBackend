from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class ControlDocumentacion(Base):
    __tablename__ = "control_documentacion"

    id_control_documentacion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_detalle_programa_alumno = Column(Integer, ForeignKey("detalle_programa_alumno.id_detalle_programa_alumno"), nullable=False)
    id_requisito = Column(Integer, ForeignKey("requisitos.id_requisito"), nullable=False)
    url_documento = Column(String(500), nullable=True)
    obligatorio = Column(Boolean, default=False, nullable=False)
    estado = Column(String(20), nullable=False, default="pendiente")
    fecha_entrega = Column(Date, nullable=True)
    fecha_revision = Column(Date, nullable=True)
    observaciones = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    detalle_programa_alumno = relationship("DetalleProgramaAlumno", back_populates="control_documentacion")
    requisito = relationship("Requisito", back_populates="control_documentacion")