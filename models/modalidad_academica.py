from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class ModalidadAcademica(Base):
    __tablename__ = "modalidades_academicas"

    id_modalidad_academica = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre_modalidad = Column(String(100), nullable=False, unique=True)
    descripcion = Column(String(500), nullable=True)
    requiere_titulo = Column(Boolean, default=False, nullable=False)
    estado = Column(String(20), nullable=False, default="activo")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    requisitos = relationship("Requisito", back_populates="modalidad_academica")
    tipos_descuento = relationship("TipoDescuento", secondary="modalidad_tipo_descuento", back_populates="modalidades")
    tipos_programa = relationship("TipoPrograma", secondary="modalidad_tipo_programa", back_populates="modalidades")
    detalles_alumno = relationship("DetalleProgramaAlumno", back_populates="modalidad_academica")
