from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class TipoPrograma(Base):
    __tablename__ = "tipos_programa"

    id_tipo_programa = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)
    estado = Column(String(20), nullable=False, default="activo")
    cupo_minimo = Column(Integer, nullable=True)
    duracion_minima_meses = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    programas = relationship("Programa", back_populates="tipo_programa")

