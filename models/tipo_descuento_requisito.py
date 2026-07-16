from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from database import Base


class TipoDescuentoRequisito(Base):
    __tablename__ = "tipo_descuento_requisito"

    id_tipo_descuento = Column(
        Integer,
        ForeignKey("tipos_descuento.id_tipo_descuento"),
        primary_key=True,
    )
    id_requisito = Column(
        Integer,
        ForeignKey("requisitos.id_requisito"),
        primary_key=True,
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
