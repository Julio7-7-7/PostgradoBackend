from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class EtapaRequisito(Base):
    __tablename__ = "etapa_requisito"

    id_etapa = Column(
        Integer,
        ForeignKey("etapa_contratacion.id_etapa"),
        primary_key=True,
    )
    id_requisito = Column(
        Integer,
        ForeignKey("requisitos.id_requisito"),
        primary_key=True,
    )
    orden = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    requisito = relationship("Requisito")
