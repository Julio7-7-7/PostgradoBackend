from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class RolesPermiso(Base):
    __tablename__ = "roles_permisos"

    id_rol = Column(Integer, ForeignKey("roles.id_rol"), primary_key=True)
    id_permiso = Column(Integer, ForeignKey("permisos.id_permiso"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    rol = relationship("Rol", back_populates="roles_permisos")
    permiso = relationship("Permiso", back_populates="roles_permisos")
