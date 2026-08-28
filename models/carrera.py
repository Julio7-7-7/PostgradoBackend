from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Carrera(Base):
    __tablename__ = "carreras"

    id_carrera = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(200), nullable=False, unique=True)
    sigla = Column(String(30), nullable=True)
    descripcion = Column(Text, nullable=True)
    estado = Column(String(20), nullable=False, default="activo")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    detalles_alumno = relationship("DetalleProgramaAlumno", back_populates="carrera")