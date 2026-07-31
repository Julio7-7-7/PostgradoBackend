from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class SolicitudIncorporacion(Base):
    __tablename__ = "solicitud_incorporacion"

    id_solicitud = Column(Integer, ForeignKey("solicitud.id_solicitud"), primary_key=True)
    id_programa_version_edicion = Column(
        Integer, ForeignKey("programa_version_edicion.id_programa_version_edicion"), nullable=False
    )
    id_modalidad_academica = Column(
        Integer, ForeignKey("modalidades_academicas.id_modalidad_academica"), nullable=False
    )
    id_tipo_descuento = Column(
        Integer, ForeignKey("tipos_descuento.id_tipo_descuento"), nullable=True
    )

    solicitud = relationship("Solicitud", back_populates="incorporacion")
    programa_version_edicion = relationship("ProgramaVersionEdicion")
    modalidad_academica = relationship("ModalidadAcademica")
