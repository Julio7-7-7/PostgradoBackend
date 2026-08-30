from sqlalchemy import Column, Integer, Date, DateTime, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class CertificadoNotas(Base):
    __tablename__ = "certificados_notas"
    __table_args__ = (
        UniqueConstraint('id_alumno', 'id_programa_version_edicion', name='uq_certificado_alumno_edicion'),
        UniqueConstraint('id_programa_version_edicion', 'numero_certificado', name='uq_certificado_numero_edicion'),
    )

    id_certificado = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_alumno = Column(Integer, ForeignKey("alumnos.id_alumno"), nullable=False)
    id_programa_version_edicion = Column(Integer, ForeignKey("programa_version_edicion.id_programa_version_edicion"), nullable=False)
    id_informe = Column(Integer, ForeignKey("informes_notas.id_informe"), nullable=True)
    fecha_emision = Column(Date, nullable=False, default=func.current_date())
    ruta_pdf = Column(Text, nullable=True)
    emitido_por = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    emitido_at = Column(DateTime(timezone=True), nullable=True)
    datos = Column(JSONB, nullable=True)
    procedencia = Column(String(20), nullable=False, default="informe")
    numero_certificado = Column(Integer, nullable=True)
    codigo = Column(String(30), nullable=True)
    n_impresiones = Column(Integer, nullable=False, default=0)
    ultima_impresion_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    alumno = relationship("Alumno")
    programa_version_edicion = relationship("ProgramaVersionEdicion")
    informe = relationship("InformeNotas", back_populates="certificados")