from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Administrativo(Base):
    __tablename__ = "administrativos"

    id_administrativo = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ci = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    cargo = Column(String(50), nullable=True)
    correo = Column(String(100), nullable=True)
    celular = Column(String(20), nullable=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    estado = Column(String(20), nullable=False, default="activo")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    usuario = relationship("Usuario", back_populates="administrativo")
