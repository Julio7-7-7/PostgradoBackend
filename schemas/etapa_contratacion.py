from pydantic import BaseModel, ConfigDict, model_validator
from datetime import datetime


class EtapaRequisitoAsignar(BaseModel):
    id_requisito: int
    orden: int = 1


class EtapaRequisitoResponse(BaseModel):
    id_requisito: int
    nombre: str
    orden: int

    model_config = ConfigDict(from_attributes=True)


class EtapaContratacionCreate(BaseModel):
    id_tipo_programa: int
    nombre: str
    orden: int | None = None
    requisitos: list[EtapaRequisitoAsignar] = []


class EtapaContratacionUpdate(BaseModel):
    nombre: str | None = None
    orden: int | None = None


class EtapaContratacionResponse(BaseModel):
    id_etapa: int
    id_tipo_programa: int
    nombre: str
    orden: int
    requisitos: list[EtapaRequisitoResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def transform_requisitos(cls, data):
        if hasattr(data, "etapa_requisitos"):
            requisitos = []
            for er in data.etapa_requisitos:
                if hasattr(er, "requisito") and er.requisito:
                    requisitos.append({
                        "id_requisito": er.requisito.id_requisito,
                        "nombre": er.requisito.nombre,
                        "orden": er.orden,
                    })
            data.requisitos = requisitos
        return data
