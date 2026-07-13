from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Requisito(Base):
    __tablename__ = "requisitos"

    id_requisito = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_modalidad_academica = Column(Integer, ForeignKey("modalidades_academicas.id_modalidad_academica"), nullable=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(String(500), nullable=True)
    obligatorio = Column(Boolean, default=True, nullable=False)
    estado = Column(String(20), nullable=False, default="activo")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('nombre', 'id_modalidad_academica', name='uq_requisito_nombre_modalidad'),
    )

    modalidad_academica = relationship("ModalidadAcademica", back_populates="requisitos")
    control_documentacion = relationship("ControlDocumentacion", back_populates="requisito")
    tipos_descuento = relationship("TipoDescuento", secondary="tipo_descuento_requisito", back_populates="requisitos")
