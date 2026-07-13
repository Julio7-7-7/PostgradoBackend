from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class TipoDescuento(Base):
    __tablename__ = "tipos_descuento"

    id_tipo_descuento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)
    porcentaje = Column(Float, nullable=False)
    descripcion = Column(String(500), nullable=True)
    estado = Column(String(20), nullable=False, default="activo")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    modalidades = relationship("ModalidadAcademica", secondary="modalidad_tipo_descuento", back_populates="tipos_descuento")
    requisitos = relationship("Requisito", secondary="tipo_descuento_requisito", back_populates="tipos_descuento")
    detalles_alumno = relationship("DetalleProgramaAlumno", back_populates="tipo_descuento")
