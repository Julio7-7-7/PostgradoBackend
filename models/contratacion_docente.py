from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import text
from database import Base


class ContratacionDocente(Base):
    __tablename__ = "contratacion_docente"
    __table_args__ = (
        Index(
            "uq_contratacion_vigente",
            "id_detalle_modulo",
            unique=True,
            postgresql_where=text("estado != 'truncado'"),
        ),
    )

    id_contratacion = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_docente = Column(Integer, ForeignKey("docentes.id_docente"), nullable=False)
    id_detalle_modulo = Column(
        Integer,
        ForeignKey("detalle_programa_modulo.id_detalle_programa_modulo"),
        nullable=False,
    )
    monto = Column(Numeric(10, 2), nullable=True)
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    estado = Column(String(30), nullable=False, default="pendiente")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    docente = relationship("Docente", back_populates="contrataciones")
    detalle_modulo = relationship("DetalleProgramaModulo", back_populates="contrataciones")

    documentos = relationship(
        "DocumentoContratacion",
        back_populates="contratacion",
        cascade="all, delete-orphan",
    )

    @property
    def id_programa(self) -> int:
        return self.detalle_modulo.programa_version_edicion.programa_version.id_programa

    @property
    def programa_nombre(self) -> str:
        return self.detalle_modulo.programa_version_edicion.programa_version.programa.nombre_programa

    @property
    def modulo_sigla(self) -> str:
        return self.detalle_modulo.modulo.sigla

    @property
    def modulo_nombre(self) -> str:
        return self.detalle_modulo.modulo.nombre_modulo
