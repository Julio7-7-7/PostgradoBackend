from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from dependencies import get_current_user, require_permiso
from models.programa import Programa
from models.docente import Docente
from models.tipo_programa import TipoPrograma
from models.alumno import Alumno
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.pago import Pago
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/stats")
def stats(db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("programas.ver"))):
    total_programas = db.query(func.count(Programa.id_programa)).scalar() or 0
    total_docentes = db.query(func.count(Docente.id_docente)).scalar() or 0
    total_tipos = db.query(func.count(TipoPrograma.id_tipo_programa)).scalar() or 0
    total_alumnos = db.query(func.count(Alumno.id_alumno)).scalar() or 0

    total_inscripciones = db.query(func.count(DetalleProgramaAlumno.id_detalle_programa_alumno)).scalar() or 0
    inscripciones_activas = db.query(func.count(DetalleProgramaAlumno.id_detalle_programa_alumno)).filter(
        DetalleProgramaAlumno.estado.in_(["inscrito", "incorporado"])
    ).scalar() or 0

    total_pagos_confirmados = db.query(func.count(Pago.id_pago)).filter(
        Pago.estado == "confirmado"
    ).scalar() or 0
    monto_total_pagos = db.query(func.coalesce(func.sum(Pago.monto), 0)).filter(
        Pago.estado == "confirmado"
    ).scalar() or 0

    return {
        "total_programas": total_programas,
        "total_docentes": total_docentes,
        "total_tipos": total_tipos,
        "total_alumnos": total_alumnos,
        "total_inscripciones": total_inscripciones,
        "inscripciones_activas": inscripciones_activas,
        "total_pagos_confirmados": total_pagos_confirmados,
        "monto_total_pagos": float(monto_total_pagos),
    }
