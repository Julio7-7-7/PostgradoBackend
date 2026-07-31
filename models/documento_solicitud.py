from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class DocumentoSolicitud(Base):
    __tablename__ = "documento_solicitud"

    id_solicitud_documento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_solicitud = Column(Integer, ForeignKey("solicitud.id_solicitud"), nullable=False)
    id_requisito = Column(Integer, ForeignKey("requisitos.id_requisito"), nullable=False)
    url_documento = Column(String(500), nullable=False)
    estado = Column(String(20), nullable=False, default="pendiente")
    fecha_entrega = Column(DateTime, nullable=True)

    solicitud = relationship("Solicitud", back_populates="documentos")
    requisito = relationship("Requisito")
