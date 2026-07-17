from enum import Enum


class GeneroEnum(str, Enum):
    masculino = "masculino"
    femenino = "femenino"


class ModalidadEnum(str, Enum):
    presencial = "presencial"
    virtual = "virtual"
    semipresencial = "semipresencial"
