from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class TipoDescuento(Base):
    __tablename__ = "tipos_descuento"

    id_tipo_descuento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)
    porcentaje = Column(Numeric(5, 2), nullable=False)
    descripcion = Column(String(500), nullable=True)
    uso_unico = Column(Boolean, default=False, nullable=False)
    estado = Column(String(20), nullable=False, default="activo")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("porcentaje > 0 AND porcentaje <= 100", name="ck_porcentaje_rango"),
        CheckConstraint("estado IN ('activo', 'inactivo')", name="ck_estado_valor"),
    )

    modalidades = relationship("ModalidadAcademica", secondary="modalidad_tipo_descuento", back_populates="tipos_descuento")
    requisitos = relationship("Requisito", secondary="tipo_descuento_requisito", back_populates="tipos_descuento")
    detalles_alumno = relationship("DetalleProgramaAlumno", back_populates="tipo_descuento")
