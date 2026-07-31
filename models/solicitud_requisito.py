from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class SolicitudRequisito(Base):
    __tablename__ = "solicitud_requisito"

    id_solicitud_requisito = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_requisito = Column(Integer, ForeignKey("requisitos.id_requisito"), nullable=False)
    id_tipo_solicitud = Column(Integer, ForeignKey("tipo_solicitud.id_tipo_solicitud"), nullable=False)
    estado = Column(String(20), nullable=False, default="activo")

    requisito = relationship("Requisito")
    tipo_solicitud = relationship("TipoSolicitud")
