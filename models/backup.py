from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from database import Base


class Backup(Base):
    __tablename__ = "backups"

    id_backup = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(250), nullable=False)
    ruta = Column(Text, nullable=False)
    tamano_bytes = Column(Integer, nullable=False, default=0)
    origen = Column(String(20), nullable=False, default="manual")  # manual | auto | previo_a_restaurar
    estado = Column(String(20), nullable=False, default="ok")  # ok | error
    observacion = Column(Text, nullable=True)
    creado_por_id_usuario = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
