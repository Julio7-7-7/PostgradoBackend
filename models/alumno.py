from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Alumno(Base):
    __tablename__ = "alumnos"

    id_alumno = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ci = Column(String(20), nullable=True, unique=True)
    pasaporte = Column(String(30), nullable=True, unique=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    fecha_nacimiento = Column(Date, nullable=True)
    genero = Column(String(20), nullable=True)
    celular = Column(String(20), nullable=True)
    correo = Column(String(100), nullable=False)
    direccion = Column(String(300), nullable=True)
    estado = Column(String(20), nullable=False, default="activo")
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    detalles_alumno = relationship("DetalleProgramaAlumno", back_populates="alumno")
    usuario = relationship("Usuario", back_populates="alumno")