from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Requisito(Base):
    __tablename__ = "requisitos"

    id_requisito = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(200), nullable=False, unique=True)
    descripcion = Column(String(500), nullable=True)
    imagen_url = Column(String(500), nullable=True)
    estado = Column(String(20), nullable=False, default="activo")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    modalidades = relationship("ModalidadAcademica", secondary="modalidad_requisito", back_populates="requisitos")
    control_documentacion = relationship("ControlDocumentacion", back_populates="requisito")
    tipos_descuento = relationship("TipoDescuento", secondary="tipo_descuento_requisito", back_populates="requisitos")
