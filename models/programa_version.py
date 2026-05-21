from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class ProgramaVersion(Base):
    __tablename__ = "programas_version"

    __table_args__ = (
        UniqueConstraint('id_programa', 'version', name='uq_programa_version'),
    )

    id_programa_version = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_programa = Column(Integer, ForeignKey("programas.id_programa"), nullable=False)
    version = Column(Integer, nullable=False)
    descripcion = Column(String(500), nullable=True)
    foto = Column(String(500), nullable=True)
    vigente = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    programa = relationship("Programa", back_populates="versiones")
    modulos = relationship("Modulo", back_populates="programa_version")
    ediciones = relationship("ProgramaVersionEdicion", back_populates="programa_version")