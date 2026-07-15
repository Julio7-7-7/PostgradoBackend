from sqlalchemy import Column, Integer, ForeignKey
from database import Base


class ModalidadRequisito(Base):
    __tablename__ = "modalidad_requisito"

    id_modalidad_academica = Column(
        Integer,
        ForeignKey("modalidades_academicas.id_modalidad_academica", ondelete="CASCADE"),
        primary_key=True,
    )
    id_requisito = Column(
        Integer,
        ForeignKey("requisitos.id_requisito", ondelete="CASCADE"),
        primary_key=True,
    )
