from datetime import date, datetime
from pydantic import BaseModel


class CertificadoNotasResponse(BaseModel):
    id_certificado: int
    id_alumno: int
    id_programa_version_edicion: int
    id_informe: int
    fecha_emision: date
    ruta_pdf: str | None
    created_at: datetime
    updated_at: datetime
