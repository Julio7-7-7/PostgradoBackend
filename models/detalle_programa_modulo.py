from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class DetalleProgramaModulo(Base):
    __tablename__ = "detalle_programa_modulo"
    __table_args__ = (
        UniqueConstraint('id_programa_version_edicion', 'orden', name='uq_detalle_orden_edicion'),
    )

    id_detalle_programa_modulo = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_programa_version_edicion = Column(Integer, ForeignKey("programa_version_edicion.id_programa_version_edicion"), nullable=False)
    id_modulo = Column(Integer, ForeignKey("modulos.id_modulo"), nullable=False)
    modalidad = Column(String(50), nullable=True)
    orden = Column(Integer, nullable=False)
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    estado = Column(String(20), nullable=False, default="programado")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    programa_version_edicion = relationship("ProgramaVersionEdicion", back_populates="detalles_modulo")
    modulo = relationship("Modulo", back_populates="detalles")
    contrataciones = relationship("ContratacionDocente", back_populates="detalle_modulo")
    historial = relationship("HistorialModulo", back_populates="detalle_programa_modulo")
    horarios = relationship("Horario", back_populates="detalle_programa_modulo")

    @property
    def id_programa_version(self) -> int:
        return self.programa_version_edicion.id_programa_version

    @property
    def id_programa(self) -> int:
        return self.programa_version_edicion.programa_version.id_programa

    @property
    def edicion(self) -> int:
        return self.programa_version_edicion.edicion

    @property
    def programa_nombre(self) -> str:
        return self.programa_version_edicion.programa_version.programa.nombre_programa

    @property
    def programa_version_numero(self) -> int:
        return self.programa_version_edicion.programa_version.version