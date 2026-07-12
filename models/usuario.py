from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(200), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    usuario_roles = relationship("UsuarioRol", back_populates="usuario", cascade="all, delete-orphan")
    alumno = relationship("Alumno", back_populates="usuario", uselist=False)
    docente = relationship("Docente", back_populates="usuario", uselist=False)
    administrativo = relationship("Administrativo", back_populates="usuario", uselist=False)

    @property
    def roles(self):
        return [ur.rol for ur in self.usuario_roles if ur.rol]

    @property
    def rol_activo(self):
        for ur in self.usuario_roles:
            if ur.rol_activo:
                return ur.rol
        return self.usuario_roles[0].rol if self.usuario_roles else None

    @property
    def id_rol_activo(self):
        rol = self.rol_activo
        return rol.id_rol if rol else None
