from sqlalchemy import Column, Integer, Date, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class CertificadoNotas(Base):
    __tablename__ = "certificados_notas"
    __table_args__ = (
        UniqueConstraint('id_alumno', 'id_programa_version_edicion', name='uq_certificado_alumno_edicion'),
    )

    id_certificado = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_alumno = Column(Integer, ForeignKey("alumnos.id_alumno"), nullable=False)
    id_programa_version_edicion = Column(Integer, ForeignKey("programa_version_edicion.id_programa_version_edicion"), nullable=False)
    id_informe = Column(Integer, ForeignKey("informes_notas.id_informe"), nullable=False)
    fecha_emision = Column(Date, nullable=False, default=func.current_date())
    ruta_pdf = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    alumno = relationship("Alumno")
    programa_version_edicion = relationship("ProgramaVersionEdicion")
    informe = relationship("InformeNotas", back_populates="certificados")
