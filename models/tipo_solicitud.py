from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base


class TipoSolicitud(Base):
    __tablename__ = "tipo_solicitud"

    id_tipo_solicitud = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo = Column(String(30), nullable=False, unique=True)
    nombre = Column(String(100), nullable=False)

    solicitudes = relationship("Solicitud", back_populates="tipo")
