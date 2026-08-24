from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class EtapaContratacion(Base):
    __tablename__ = "etapa_contratacion"

    id_etapa = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_tipo_programa = Column(Integer, ForeignKey("tipos_programa.id_tipo_programa"), nullable=False)
    nombre = Column(String(200), nullable=False)
    orden = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    tipo_programa = relationship("TipoPrograma", backref="etapas_contratacion")
    etapa_requisitos = relationship("EtapaRequisito", cascade="all, delete-orphan")
