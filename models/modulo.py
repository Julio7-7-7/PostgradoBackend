from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Modulo(Base):
    __tablename__ = "modulos"

    id_modulo = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_programa_version = Column(Integer, ForeignKey("programas_version.id_programa_version"), nullable=False)
    sigla = Column(String(20), nullable=False, unique=True)
    nombre_modulo = Column(String(200), nullable=False)
    horas_academicas = Column(Integer, nullable=False)
    creditos = Column(Integer, nullable=False)
    descripcion = Column(String(500), nullable=True)
    estado = Column(String(20), nullable=False, default="activo")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    programa_version = relationship("ProgramaVersion", back_populates="modulos")
    detalles = relationship("DetalleProgramaModulo", back_populates="modulo")