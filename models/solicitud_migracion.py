from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class SolicitudMigracion(Base):
    __tablename__ = "solicitud_migracion"

    id_solicitud = Column(Integer, ForeignKey("solicitud.id_solicitud"), primary_key=True)
    id_edicion_destino = Column(
        Integer, ForeignKey("programa_version_edicion.id_programa_version_edicion"), nullable=False
    )
    motivo = Column(Text, nullable=False, default="")

    solicitud = relationship("Solicitud", back_populates="migracion")
    edicion_destino = relationship("ProgramaVersionEdicion")
