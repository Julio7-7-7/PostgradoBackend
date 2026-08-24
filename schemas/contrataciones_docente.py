from pydantic import BaseModel, ConfigDict, model_validator
from datetime import datetime, date
from enum import Enum
from schemas.docente import DocenteResponse


class ContratacionEstadoEnum(str, Enum):
    pendiente = "pendiente"
    verificacion = "verificacion"
    convocatoria = "convocatoria"
    seleccion = "seleccion"
    resolucion = "resolucion"
    legal = "legal"
    formalizado = "formalizado"
    truncado = "truncado"


class ContratacionDocenteBase(BaseModel):
    id_docente: int
    id_detalle_modulo: int
    monto: float | None = None


class ContratacionDocenteCreate(ContratacionDocenteBase):
    pass


class ContratacionDocenteUpdate(BaseModel):
    monto: float | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    estado: ContratacionEstadoEnum | None = None


class ContratacionDocenteResponse(ContratacionDocenteBase):
    id_contratacion: int
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    estado: ContratacionEstadoEnum
    id_etapa_actual: int | None = None
    etapa_actual_nombre: str = ""
    docente: DocenteResponse
    id_programa: int = 0
    programa_nombre: str = ""
    modulo_sigla: str = ""
    modulo_nombre: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def fill_derived_fields(cls, data):
        if hasattr(data, 'detalle_modulo') and data.detalle_modulo is not None:
            if data.fecha_inicio is None and data.detalle_modulo.fecha_inicio:
                data.fecha_inicio = data.detalle_modulo.fecha_inicio
            if data.fecha_fin is None and data.detalle_modulo.fecha_fin:
                data.fecha_fin = data.detalle_modulo.fecha_fin
            modulo = getattr(data.detalle_modulo, 'modulo', None)
            if modulo:
                object.__setattr__(data, 'modulo_sigla', modulo.sigla or "")
                object.__setattr__(data, 'modulo_nombre', modulo.nombre_modulo or "")
            pve = getattr(data.detalle_modulo, 'programa_version_edicion', None)
            if pve:
                pv = getattr(pve, 'programa_version', None)
                if pv:
                    object.__setattr__(data, 'id_programa', pv.id_programa or 0)
                    prog = getattr(pv, 'programa', None)
                    if prog:
                        object.__setattr__(data, 'programa_nombre', prog.nombre_programa or "")
        etapa = getattr(data, 'etapa_actual', None)
        if etapa:
            object.__setattr__(data, 'etapa_actual_nombre', getattr(etapa, 'nombre', '') or '')
        return data
