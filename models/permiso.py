from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Permiso(Base):
    __tablename__ = "permisos"

    id_permiso = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo = Column(String(100), unique=True, nullable=False)
    descripcion = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    roles_permisos = relationship("RolesPermiso", back_populates="permiso", cascade="all, delete-orphan")
