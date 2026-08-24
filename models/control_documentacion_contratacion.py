from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class ControlDocumentacionContratacion(Base):
    __tablename__ = "control_documentacion_contratacion"

    id_control_doc_contratacion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_contratacion = Column(Integer, ForeignKey("contratacion_docente.id_contratacion"), nullable=False)
    id_requisito = Column(Integer, ForeignKey("requisitos.id_requisito"), nullable=False)
    id_etapa = Column(Integer, ForeignKey("etapa_contratacion.id_etapa"), nullable=False)
    url_documento = Column(String(500), nullable=True)
    estado = Column(String(20), nullable=False, default="pendiente")
    notas = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    contratacion = relationship("ContratacionDocente", back_populates="documentos")
    requisito = relationship("Requisito")
    etapa = relationship("EtapaContratacion")
