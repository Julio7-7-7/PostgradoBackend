from enum import Enum
import math


class GeneroEnum(str, Enum):
    masculino = "masculino"
    femenino = "femenino"


class ModalidadEnum(str, Enum):
    presencial = "presencial"
    virtual = "virtual"
    semipresencial = "semipresencial"


class NotaCalificacion(str, Enum):
    ABANDONO = "abandono"
    INSUFICIENTE = "insuficiente"
    SUFICIENTE = "suficiente"
    BUENO = "bueno"
    DISTINGUIDO = "distinguido"
    SOBRESALIENTE = "sobresaliente"


ESTADOS_CON_CALIFICACION = {"inscrito", "incorporado", "finalizado", "graduado"}


def clasificar_nota(nota: float) -> NotaCalificacion:
    if nota == 0:
        return NotaCalificacion.ABANDONO
    if nota <= 65:
        return NotaCalificacion.INSUFICIENTE
    if nota <= 70:
        return NotaCalificacion.SUFICIENTE
    if nota <= 80:
        return NotaCalificacion.BUENO
    if nota <= 90:
        return NotaCalificacion.DISTINGUIDO
    return NotaCalificacion.SOBRESALIENTE


def redondear_nota(nota: float) -> int:
    return math.floor(nota + 0.5)
