from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Docente(Base):
    __tablename__ = "docentes"

    id_docente = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ci = Column(String(20), nullable=False, unique=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    genero = Column(String(20), nullable=True)
    extension = Column(String(5), nullable=True)
    grado = Column(String(50), nullable=True)
    titulo = Column(String(100), nullable=True)
    celular = Column(String(20), nullable=True)
    correo = Column(String(100), nullable=False, unique=True)
    estado = Column(String(20), nullable=False, default="disponible")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    detalles = relationship("DetalleProgramaModulo", back_populates="docente")