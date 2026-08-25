from sqlalchemy.orm import Session
from models.programa_version_edicion import ProgramaVersionEdicion
from models.detalle_programa_modulo import DetalleProgramaModulo


def actualizar_estado_edicion(id_edicion: int, db: Session) -> bool:
    """Calcula y actualiza el estado de una edición según el estado de sus módulos."""
    edicion = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id_edicion
    ).first()
    if not edicion:
        return False

    detalles = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == id_edicion
    ).all()
    if not detalles:
        return False

    estados = [d.estado for d in detalles]

    if all(e == "finalizado" for e in estados):
        nuevo = "finalizado"
    elif any(e == "reprogramado" for e in estados) and not any(e == "finalizado" for e in estados):
        nuevo = "reprogramado"
    elif any(e in ("en_curso", "reprogramado") for e in estados):
        nuevo = "en_curso"
    elif any(e == "finalizado" for e in estados):
        nuevo = "en_curso"
    else:
        nuevo = "programado"

    if edicion.estado != nuevo:
        edicion.estado = nuevo
        return True
    return False
