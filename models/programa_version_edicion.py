from sqlalchemy import Column, Integer, String, Boolean, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class ProgramaVersionEdicion(Base):
    __tablename__ = "programa_version_edicion"

    id_programa_version_edicion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_programa_version = Column(Integer, ForeignKey("programas_version.id_programa_version"), nullable=False)
    modalidad = Column(String(50), nullable=False, default="presencial")
    edicion = Column(Integer, nullable=False)
    gestion = Column(String(10), nullable=False)
    estado = Column(String(20), nullable=False, default="programado")
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    cupo_maximo = Column(Integer, nullable=True)
    descripcion = Column(String(500), nullable=True)
    precio = Column(Float, nullable=True)
    es_historico = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    programa_version = relationship("ProgramaVersion", back_populates="ediciones")
    detalles_modulo = relationship("DetalleProgramaModulo", back_populates="programa_version_edicion")
    detalles_alumno = relationship("DetalleProgramaAlumno", back_populates="programa_version_edicion")