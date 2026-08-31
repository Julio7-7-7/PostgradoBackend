from sqlalchemy import Column, Integer, Date, DateTime, Text, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class InformeNotas(Base):
    __tablename__ = "informes_notas"
    __table_args__ = (
        UniqueConstraint('id_programa_version_edicion', 'numero_tanda', name='uq_informe_edicion_tanda'),
    )

    id_informe = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_programa_version_edicion = Column(Integer, ForeignKey("programa_version_edicion.id_programa_version_edicion"), nullable=False)
    numero_tanda = Column(Integer, nullable=True)
    tipo = Column(String(20), nullable=False, default="borrador")
    fecha_emision = Column(Date, nullable=False, default=func.current_date())
    generado_at = Column(DateTime, server_default=func.now(), nullable=True)
    alumnos_ids = Column(JSONB, nullable=False, default=list)
    contenido = Column(JSONB, nullable=True)
    estado = Column(String(20), nullable=False, default="enviado")
    observaciones = Column(Text, nullable=True)
    emitido_por = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    emitido_por_nombre = Column(String(120), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    programa_version_edicion = relationship("ProgramaVersionEdicion")
    certificados = relationship("CertificadoNotas", back_populates="informe")
