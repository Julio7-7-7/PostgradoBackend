from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models.certificado_notas import CertificadoNotas
from models.alumno import Alumno
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.programa_version_edicion import ProgramaVersionEdicion
from models.nota import Nota
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.modulo import Modulo
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/certificados-notas",
    tags=["Certificados de Notas"],
    dependencies=[Depends(get_current_user)],
)


def _serializar_certificado(cert, alumno=None, edicion=None, notas=None) -> dict:
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
            "programa": None,
            "edicion": edicion.edicion if edicion else None,
            "anio": edicion.anio if edicion else None,
            "semestre": edicion.semestre if edicion else None,
        } if edicion else None,
        "notas": notas or [],
    }


@router.get("/mis-certificados/{id_alumno}")
def mis_certificados(
    id_alumno: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    es_el_alumno = current_user.profile_type == "alumno" and current_user.id_profile == id_alumno
    if not es_el_alumno:
        if not any(p.codigo == "pagos.ver" for p in current_user.permisos):
            raise HTTPException(status_code=403, detail="No tenés permiso para ver certificados")

    certificados = db.query(CertificadoNotas).filter(
        CertificadoNotas.id_alumno == id_alumno
    ).order_by(CertificadoNotas.created_at.desc()).all()

    resultado = []
    for cert in certificados:
        alumno = db.query(Alumno).filter(Alumno.id_alumno == cert.id_alumno).first()
        edicion = db.query(ProgramaVersionEdicion).filter(
            ProgramaVersionEdicion.id_programa_version_edicion == cert.id_programa_version_edicion
        ).first()

        dpa = db.query(DetalleProgramaAlumno).filter(
            DetalleProgramaAlumno.id_alumno == id_alumno,
            DetalleProgramaAlumno.id_programa_version_edicion == cert.id_programa_version_edicion,
        ).first()

        notas_data = []
        if dpa:
            notas = db.query(Nota).filter(
                Nota.id_detalle_programa_alumno == dpa.id_detalle_programa_alumno
            ).all()
            for n in notas:
                dpm = db.query(DetalleProgramaModulo).filter(
                    DetalleProgramaModulo.id_detalle_programa_modulo == n.id_detalle_programa_modulo
                ).first()
                mod = db.query(Modulo).filter(
                    Modulo.id_modulo == dpm.id_modulo
                ).first() if dpm else None
                notas_data.append({
                    "modulo": mod.nombre_modulo if mod else "N/A",
                    "sigla": mod.sigla if mod else "",
                    "nota": float(n.nota),
                    "orden": dpm.orden if dpm else 0,
                })
            notas_data.sort(key=lambda x: x["orden"])

        pv = edicion.programa_version if edicion else None
        prog = pv.programa if pv else None
        resultado.append(_serializar_certificado(cert, alumno, edicion, notas_data))
        if resultado:
            resultado[-1]["edicion"]["programa"] = prog.nombre_programa if prog else None

    return {"id_alumno": id_alumno, "certificados": resultado}
