from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Programa(Base):
    __tablename__ = "programas"

    id_programa = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_tipo_programa = Column(Integer, ForeignKey("tipos_programa.id_tipo_programa"), nullable=False)
    nombre_programa = Column(String(200), nullable=False, unique=True)
    foto = Column(String(500), nullable=True)
    estado = Column(String(20), nullable=False, default="activo")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    tipo_programa = relationship("TipoPrograma", back_populates="programas")
    versiones = relationship("ProgramaVersion", back_populates="programa")