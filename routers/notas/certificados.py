from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_permiso
from models.certificado_notas import CertificadoNotas
from models.alumno import Alumno
from models.programa_version_edicion import ProgramaVersionEdicion
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/certificados-notas",
    tags=["Certificados de Notas"],
    dependencies=[Depends(get_current_user)],
)


def _serializar_certificado(cert, alumno=None, edicion=None, programa=None) -> dict:
    return {
        "id_certificado": cert.id_certificado,
        "id_alumno": cert.id_alumno,
        "id_programa_version_edicion": cert.id_programa_version_edicion,
        "id_informe": cert.id_informe,
        "fecha_emision": str(cert.fecha_emision),
        "ruta_pdf": cert.ruta_pdf,
        "alumno": {
            "nombre": alumno.nombre if alumno else None,
            "apellido": alumno.apellido if alumno else None,
            "ci": alumno.ci if alumno else None,
        } if alumno else None,
        "edicion": {
            "programa": programa.nombre_programa if programa else None,
            "edicion": edicion.edicion if edicion else None,
            "anio": edicion.anio if edicion else None,
            "semestre": edicion.semestre if edicion else None,
        } if edicion else None,
    }


@router.get("/por-informe/{id_informe}")
def certificados_por_informe(
    id_informe: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver")),
):
    certificados = db.query(CertificadoNotas).filter(
        CertificadoNotas.id_informe == id_informe
    ).order_by(CertificadoNotas.id_certificado).all()

    alumno_ids = {c.id_alumno for c in certificados}
    alumnos_map = {
        a.id_alumno: a
        for a in db.query(Alumno).filter(Alumno.id_alumno.in_(alumno_ids)).all()
    } if alumno_ids else {}

    resultado = []
    for cert in certificados:
        edicion = db.query(ProgramaVersionEdicion).filter(
            ProgramaVersionEdicion.id_programa_version_edicion == cert.id_programa_version_edicion
        ).first()
        programa = None
        if edicion and edicion.programa_version:
            programa = edicion.programa_version.programa
        resultado.append(_serializar_certificado(
            cert,
            alumnos_map.get(cert.id_alumno),
            edicion,
            programa,
        ))

    return {"id_informe": id_informe, "certificados": resultado}
