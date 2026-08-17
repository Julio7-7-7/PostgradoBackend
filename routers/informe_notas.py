from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from dependencies import get_current_user, require_permiso
from models.informe_notas import InformeNotas
from models.certificado_notas import CertificadoNotas
from models.programa_version_edicion import ProgramaVersionEdicion
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.alumno import Alumno
from schemas.auth import UserResponse
from schemas.informe_notas import (
    InformeNotasCreate,
    InformeNotasResponse,
    InformeNotasAlumnoDetalle,
)

router = APIRouter(
    prefix="/informes-notas",
    tags=["Informes de Notas"],
    dependencies=[Depends(get_current_user)],
)


def _serializar_informe(informe: InformeNotas) -> dict:
    return {
        "id_informe": informe.id_informe,
        "id_programa_version_edicion": informe.id_programa_version_edicion,
        "numero_tanda": informe.numero_tanda,
        "fecha_emision": str(informe.fecha_emision),
        "alumnos_ids": informe.alumnos_ids,
        "estado": informe.estado,
        "observaciones": informe.observaciones,
        "created_at": informe.created_at.isoformat() if informe.created_at else None,
        "updated_at": informe.updated_at.isoformat() if informe.updated_at else None,
    }


def _alumnos_elegibles(db: Session, id_edicion: int) -> list[dict]:
    """Alumnos con todas las notas aprobadas + todos los pagos completos + no en tanda anterior."""
    query = text("""
        SELECT
            a.id_alumno,
            dpa.id_detalle_programa_alumno,
            a.nombre,
            a.apellido,
            a.ci
        FROM alumnos a
        JOIN detalle_programa_alumno dpa ON dpa.id_alumno = a.id_alumno
        WHERE dpa.id_programa_version_edicion = :id_edicion
          AND dpa.estado NOT IN ('retirado', 'postulante')
          -- Todas las notas aprobadas
          AND NOT EXISTS (
              SELECT 1
              FROM notas n
              JOIN detalle_programa_modulo dpm ON dpm.id_detalle_programa_modulo = n.id_detalle_programa_modulo
              WHERE dpm.id_programa_version_edicion = :id_edicion
                AND n.id_detalle_programa_alumno = dpa.id_detalle_programa_alumno
                AND n.nota < 10
          )
          -- Todos los pagos completos
          AND NOT EXISTS (
              SELECT 1
              FROM ordenes_pago op
              LEFT JOIN transacciones_pago tp ON tp.id_orden_pago = op.id_orden_pago
              WHERE op.id_detalle_programa_alumno = dpa.id_detalle_programa_alumno
                AND tp.id_transaccion IS NULL
          )
          -- No incluido en tanda anterior enviada
          AND a.id_alumno NOT IN (
              SELECT jsonb_array_elements_text(inf.alumnos_ids)::INT
              FROM informes_notas inf
              WHERE inf.id_programa_version_edicion = :id_edicion
                AND inf.estado = 'enviado'
          )
        ORDER BY a.apellido, a.nombre
    """)
    rows = db.execute(query, {"id_edicion": id_edicion}).fetchall()
    return [
        {
            "id_alumno": r.id_alumno,
            "id_detalle_programa_alumno": r.id_detalle_programa_alumno,
            "nombre": r.nombre,
            "apellido": r.apellido,
            "ci": r.ci,
        }
        for r in rows
    ]


@router.get("/elegibles/{id_edicion}")
def alumnos_elegibles(
    id_edicion: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver")),
):
    edicion = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id_edicion
    ).first()
    if not edicion:
        raise HTTPException(status_code=404, detail="Edición no encontrada")

    elegibles = _alumnos_elegibles(db, id_edicion)

    return {
        "id_programa_version_edicion": id_edicion,
        "total_elegibles": len(elegibles),
        "alumnos": elegibles,
    }


@router.get("/por-edicion/{id_edicion}")
def informes_por_edicion(
    id_edicion: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver")),
):
    informes = db.query(InformeNotas).filter(
        InformeNotas.id_programa_version_edicion == id_edicion
    ).order_by(InformeNotas.numero_tanda).all()

    return [_serializar_informe(i) for i in informes]


@router.post("/", status_code=201)
def crear_informe(
    data: InformeNotasCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.registrar")),
):
    edicion = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == data.id_programa_version_edicion
    ).first()
    if not edicion:
        raise HTTPException(status_code=404, detail="Edición no encontrada")

    existe = db.query(InformeNotas).filter(
        InformeNotas.id_programa_version_edicion == data.id_programa_version_edicion,
        InformeNotas.numero_tanda == data.numero_tanda,
    ).first()
    if existe:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe la tanda {data.numero_tanda} para esta edición",
        )

    elegibles = {e["id_alumno"] for e in _alumnos_elegibles(db, data.id_programa_version_edicion)}
    no_elegibles = [aid for aid in data.alumnos_ids if aid not in elegibles]
    if no_elegibles:
        raise HTTPException(
            status_code=400,
            detail=f"Alumnos no elegibles: {no_elegibles}. Verificar notas y pagos.",
        )

    informe = InformeNotas(
        id_programa_version_edicion=data.id_programa_version_edicion,
        numero_tanda=data.numero_tanda,
        fecha_emision=date.today(),
        alumnos_ids=data.alumnos_ids,
        estado="borrador",
        observaciones=data.observaciones,
    )
    db.add(informe)
    db.flush()

    for id_alumno in data.alumnos_ids:
        cert = CertificadoNotas(
            id_alumno=id_alumno,
            id_programa_version_edicion=data.id_programa_version_edicion,
            id_informe=informe.id_informe,
            fecha_emision=date.today(),
        )
        db.add(cert)

    db.commit()
    db.refresh(informe)
    return _serializar_informe(informe)


@router.patch("/{id_informe}/enviar")
def enviar_informe(
    id_informe: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.registrar")),
):
    informe = db.query(InformeNotas).filter(
        InformeNotas.id_informe == id_informe
    ).first()
    if not informe:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    if informe.estado == "enviado":
        raise HTTPException(status_code=400, detail="El informe ya fue enviado")

    informe.estado = "enviado"
    db.commit()
    db.refresh(informe)
    return _serializar_informe(informe)
