from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_permiso
from models.alumno import Alumno
from models.certificado_notas import CertificadoNotas
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.nota import Nota
from models.programa_version_edicion import ProgramaVersionEdicion
from routers.notas._builder_informes import (
    calcular_elegibilidad,
    datos_certificado,
    modulos_edicion,
    resolver_edicion,
    _es_educacion_continua,
)
from schemas.auth import UserResponse
from schemas.informe_notas import CertificadoEmitirRequest

router = APIRouter(
    prefix="/certificados-notas",
    tags=["Certificados de Notas"],
    dependencies=[Depends(get_current_user)],
)

ESTADOS_INCLUIDOS = ("inscrito", "incorporado", "finalizado", "graduado")
def _contexto_dpa(cert) -> dict:
    modalidad = carrera = None
    if cert.datos:
        modalidad = cert.datos.get("modalidad")
        carrera = cert.datos.get("carrera")
    return {"modalidad": modalidad, "carrera": carrera}


def _serializar_certificado(cert, alumno=None, edicion=None, programa=None) -> dict:
    base = _contexto_dpa(cert)
    return {
        "id_certificado": cert.id_certificado,
        "id_alumno": cert.id_alumno,
        "id_programa_version_edicion": cert.id_programa_version_edicion,
        "id_informe": cert.id_informe,
        "fecha_emision": str(cert.fecha_emision),
        "emitido_por": cert.emitido_por,
        "emitido_at": cert.emitido_at.isoformat() if cert.emitido_at else None,
        "procedencia": cert.procedencia,
        "numero_certificado": cert.numero_certificado,
        "codigo": cert.codigo,
        "n_impresiones": cert.n_impresiones,
        "ultima_impresion_at": cert.ultima_impresion_at.isoformat() if cert.ultima_impresion_at else None,
        "ruta_pdf": cert.ruta_pdf,
        "modalidad": base["modalidad"],
        "carrera": base["carrera"],
        "datos": cert.datos,
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


def _siguiente_numero(db: Session, id_edicion: int) -> int:
    ultimo = db.query(func.max(CertificadoNotas.numero_certificado)).filter(
        CertificadoNotas.id_programa_version_edicion == id_edicion,
        CertificadoNotas.numero_certificado.isnot(None),
    ).scalar()
    return (ultimo or 0) + 1


@router.get("/por-informe/{id_informe}")
def certificados_por_informe(
    id_informe: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver")),
):
    certificados = db.query(CertificadoNotas).filter(
        CertificadoNotas.id_informe == id_informe
    ).order_by(CertificadoNotas.numero_certificado, CertificadoNotas.id_certificado).all()

    alumno_ids = {c.id_alumno for c in certificados}
    alumnos_map = {
        a.id_alumno: a
        for a in db.query(Alumno).filter(Alumno.id_alumno.in_(alumno_ids)).all()
    } if alumno_ids else {}

    ediciones = {}
    for cert in certificados:
        if cert.id_programa_version_edicion not in ediciones:
            pve, pv, programa = resolver_edicion(db, cert.id_programa_version_edicion)
            ediciones[cert.id_programa_version_edicion] = (pve, programa)

    resultado = []
    for cert in certificados:
        pve, programa = ediciones.get(cert.id_programa_version_edicion, (None, None))
        resultado.append(_serializar_certificado(
            cert,
            alumnos_map.get(cert.id_alumno),
            pve,
            programa,
        ))

    return {"id_informe": id_informe, "certificados": resultado}


@router.get("/elegibles/{id_edicion}")
def elegibles_certificados(
    id_edicion: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver")),
):
    pve, _, _ = resolver_edicion(db, id_edicion)
    dpas = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_programa_version_edicion == id_edicion,
        DetalleProgramaAlumno.estado.in_(ESTADOS_INCLUIDOS),
    ).order_by(DetalleProgramaAlumno.id_detalle_programa_alumno).all()

    nota_map = {}
    dpa_ids = [d.id_detalle_programa_alumno for d in dpas]
    for n in db.query(Nota).filter(Nota.id_detalle_programa_alumno.in_(dpa_ids)).all():
        nota_map[(n.id_detalle_programa_alumno, n.id_detalle_programa_modulo)] = float(n.nota)
    all_dmps = [d.id_detalle_programa_modulo for d in modulos_edicion(db, id_edicion)]
    eleg = calcular_elegibilidad(db, id_edicion, dpas, nota_map, all_dmps)

    resultado = []
    for d in dpas:
        det = eleg.get(d.id_detalle_programa_alumno, {})
        resultado.append({
            "id_alumno": d.id_alumno,
            "id_detalle_programa_alumno": d.id_detalle_programa_alumno,
            "nombre": d.alumno.nombre,
            "apellido": d.alumno.apellido,
            "ci": d.alumno.ci,
            "modalidad": d.modalidad_academica.nombre_modalidad if d.modalidad_academica else None,
            "carrera": d.carrera.nombre if d.carrera else None,
            "educacion_continua": _es_educacion_continua(d),
            "elegible": det.get("elegible", False),
            "estado": det.get("estado"),
        })
    return {"id_programa_version_edicion": id_edicion, "alumnos": resultado}


@router.post("/emitir")
def emitir_certificados(
    data: CertificadoEmitirRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.registrar")),
):
    pve, _, _ = resolver_edicion(db, data.id_programa_version_edicion)
    if pve.estado != "finalizado":
        raise HTTPException(status_code=400, detail="La edición debe estar finalizada para emitir certificados")

    dpas = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_programa_version_edicion == data.id_programa_version_edicion,
        DetalleProgramaAlumno.estado.in_(ESTADOS_INCLUIDOS),
    ).all()
    dpa_map = {d.id_alumno: d for d in dpas}

    nota_map = {}
    dpa_ids = [d.id_detalle_programa_alumno for d in dpas]
    for n in db.query(Nota).filter(Nota.id_detalle_programa_alumno.in_(dpa_ids)).all():
        nota_map[(n.id_detalle_programa_alumno, n.id_detalle_programa_modulo)] = float(n.nota)
    all_dmps = [d.id_detalle_programa_modulo for d in modulos_edicion(db, data.id_programa_version_edicion)]
    eleg = calcular_elegibilidad(db, data.id_programa_version_edicion, dpas, nota_map, all_dmps)

    emitidos = []
    omitidos = []
    numero = _siguiente_numero(db, data.id_programa_version_edicion)
    now = datetime.now(timezone.utc)
    procesados = set()

    for id_alumno in data.alumnos_ids:
        if id_alumno in procesados:
            continue
        procesados.add(id_alumno)
        d = dpa_map.get(id_alumno)
        if not d:
            omitidos.append({"id_alumno": id_alumno, "motivo": "sin inscripción en la edición"})
            continue
        if _es_educacion_continua(d):
            omitidos.append({"id_alumno": id_alumno, "motivo": "educación continua (se emite con el informe final)"})
            continue
        det = eleg.get(d.id_detalle_programa_alumno, {})
        if not det.get("elegible", False):
            omitidos.append({"id_alumno": id_alumno, "motivo": det.get("estado") or "no elegible"})
            continue

        cert = CertificadoNotas(
            id_alumno=id_alumno,
            id_programa_version_edicion=data.id_programa_version_edicion,
            id_informe=None,
            fecha_emision=date.today(),
            datos=datos_certificado(db, data.id_programa_version_edicion, id_alumno),
            procedencia="individual",
            emitido_por=current_user.id_usuario,
            emitido_at=now,
            numero_certificado=numero,
            codigo=f"CERT-{pve.anio}-{numero:03d}",
            n_impresiones=0,
        )
        numero += 1
        db.add(cert)
        db.flush()
        emitidos.append(_serializar_certificado(cert))

    db.commit()
    return {"emitidos": emitidos, "omitidos": omitidos}


@router.get("/por-edicion/{id_edicion}")
def certificados_por_edicion(
    id_edicion: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver")),
):
    certificados = db.query(CertificadoNotas).filter(
        CertificadoNotas.id_programa_version_edicion == id_edicion
    ).order_by(CertificadoNotas.numero_certificado, CertificadoNotas.id_certificado).all()

    pve, _, programa = resolver_edicion(db, id_edicion)
    return [_serializar_certificado(c, None, pve, programa) for c in certificados]


@router.get("/{id_certificado}")
def obtener_certificado(
    id_certificado: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver")),
):
    cert = db.query(CertificadoNotas).filter(
        CertificadoNotas.id_certificado == id_certificado
    ).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")
    pve, _, programa = resolver_edicion(db, cert.id_programa_version_edicion)
    alumno = db.query(Alumno).filter(Alumno.id_alumno == cert.id_alumno).first()
    return _serializar_certificado(cert, alumno, pve, programa)


@router.post("/{id_certificado}/imprimir")
def registrar_impresion(
    id_certificado: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver")),
):
    cert = db.query(CertificadoNotas).filter(
        CertificadoNotas.id_certificado == id_certificado
    ).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")
    cert.n_impresiones = (cert.n_impresiones or 0) + 1
    cert.ultima_impresion_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cert)
    return {"id_certificado": cert.id_certificado, "n_impresiones": cert.n_impresiones,
            "ultima_impresion_at": cert.ultima_impresion_at.isoformat() if cert.ultima_impresion_at else None}