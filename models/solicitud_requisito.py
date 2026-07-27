from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class SolicitudRequisito(Base):
    __tablename__ = "solicitud_requisito"

    id_solicitud_requisito = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_requisito = Column(Integer, ForeignKey("requisitos.id_requisito"), nullable=False)
    obligatorio = Column(Boolean, nullable=False, default=True)
    estado = Column(String(20), nullable=False, default="activo")
    tipo = Column(String(20), nullable=False, default="incorporacion")

    requisito = relationship("Requisito")
