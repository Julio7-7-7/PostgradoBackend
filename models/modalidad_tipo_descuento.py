from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from database import Base


class ModalidadTipoDescuento(Base):
    __tablename__ = "modalidad_tipo_descuento"

    id_modalidad_academica = Column(
        Integer,
        ForeignKey("modalidades_academicas.id_modalidad_academica", ondelete="CASCADE"),
        primary_key=True,
    )
    id_tipo_descuento = Column(
        Integer,
        ForeignKey("tipos_descuento.id_tipo_descuento", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
