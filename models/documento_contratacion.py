from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class DocumentoContratacion(Base):
    __tablename__ = "documentos_contratacion"

    id_documento = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_contratacion = Column(
        Integer,
        ForeignKey("contratacion_docente.id_contratacion"),
        nullable=False,
    )
    tipo = Column(String(30), nullable=False)
    archivo_pdf = Column(String(500), nullable=True)
    fecha_subida = Column(DateTime, server_default=func.now(), nullable=False)
    orden = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    contratacion = relationship("ContratacionDocente", back_populates="documentos")
