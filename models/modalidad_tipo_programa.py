from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from database import Base


class ModalidadTipoPrograma(Base):
    __tablename__ = "modalidad_tipo_programa"

    id_modalidad_academica = Column(
        Integer,
        ForeignKey("modalidades_academicas.id_modalidad_academica"),
        primary_key=True,
    )
    id_tipo_programa = Column(
        Integer,
        ForeignKey("tipos_programa.id_tipo_programa"),
        primary_key=True,
    )
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
