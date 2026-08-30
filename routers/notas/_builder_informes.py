from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text

from models.programa_version_edicion import ProgramaVersionEdicion
from models.programa_version import ProgramaVersion
from models.programa import Programa
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.detalle_programa_alumno import DetalleProgramaAlumno
from models.nota import Nota
from models.carrera import Carrera
from models.certificado_notas import CertificadoNotas
from schemas.informe_notas import InformeNotasRequest
from schemas.enums import clasificar_nota, redondear_nota

ESTADOS_INCLUIDOS = ("inscrito", "incorporado", "finalizado", "graduado")

NOTA_APROBATORIA = 66


def _arreglar_alumno(d) -> dict:
    a = d.alumno
    return {
        "id_alumno": a.id_alumno,
        "id_detalle_programa_alumno": d.id_detalle_programa_alumno,
        "nombre": a.nombre,
        "apellido": a.apellido,
        "ci": a.ci,
    }


def _nombre_modulo(dpm: DetalleProgramaModulo) -> str:
    return dpm.modulo.nombre_modulo if dpm.modulo else f"Modulo #{dpm.id_modulo}"


def resolver_edicion(db: Session, id_edicion: int):
    pve = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == id_edicion
    ).first()
    if not pve:
        raise HTTPException(status_code=404, detail="Edicion no encontrada")
    pv = db.query(ProgramaVersion).filter(
        ProgramaVersion.id_programa_version == pve.id_programa_version
    ).first()
    programa = db.query(Programa).filter(
        Programa.id_programa == pv.id_programa
    ).first() if pv else None
    return pve, pv, programa


def modulos_edicion(db: Session, id_edicion: int):
    return db.query(DetalleProgramaModulo).options(
        joinedload(DetalleProgramaModulo.modulo)
    ).filter(
        DetalleProgramaModulo.id_programa_version_edicion == id_edicion
    ).order_by(DetalleProgramaModulo.orden).all()


def calcular_elegibilidad(db: Session, id_edicion: int, dpas: list, nota_map: dict, id_dmps: list) -> dict:
    """Cruce de elegibilidad por alumno: notas completas y aprobadas + pagos al día + sin certificado previo."""
    pagos_incompletos = set()
    con_certificado = set()
    if dpas:
        dpa_ids = [d.id_detalle_programa_alumno for d in dpas]
        pagos_incompletos = {
            row[0] for row in db.execute(text("""
                SELECT op.id_detalle_programa_alumno
                FROM orden_pago op
                LEFT JOIN transaccion_pago tp ON tp.id_orden_pago = op.id_orden_pago
                WHERE op.id_detalle_programa_alumno = ANY(:ids)
                  AND tp.id_transaccion IS NULL
            """), {"ids": dpa_ids}).fetchall()
        }
        con_certificado = {
            c.id_alumno for c in db.query(CertificadoNotas.id_alumno).filter(
                CertificadoNotas.id_programa_version_edicion == id_edicion
            ).all()
        }

    resultado = {}
    for d in dpas:
        notas = [nota_map.get((d.id_detalle_programa_alumno, m)) for m in id_dmps]
        cargadas = [n for n in notas if n is not None]
        todas = len(cargadas) == len(notas)
        aprobada = todas and all(n >= NOTA_APROBATORIA for n in notas)

        estado = None
        elegible = False
        if not todas:
            estado = "Notas pendientes"
        elif not aprobada:
            estado = "Notas reprobadas"
        elif d.id_detalle_programa_alumno in pagos_incompletos:
            estado = "Pagos incompletos"
        elif d.id_alumno in con_certificado:
            estado = "Con certificado previo"
        else:
            estado = "Completo"
            elegible = True

        resultado[d.id_detalle_programa_alumno] = {
            "notas": notas,
            "aprobada": aprobada,
            "elegible": elegible,
            "estado": estado,
            "promedio": redondear_nota(sum(cargadas) / len(cargadas)) if cargadas else None,
        }
    return resultado


def armar_contenido(db: Session, request: InformeNotasRequest) -> dict:
    pve, pv, programa = resolver_edicion(db, request.id_programa_version_edicion)
    todos_dmps = modulos_edicion(db, request.id_programa_version_edicion)
    if not todos_dmps:
        raise HTTPException(status_code=400, detail="La edicion no tiene modulos")

    es_final = request.tipo == "final"
    if es_final:
        seleccion = todos_dmps
    else:
        if not request.id_modulos:
            raise HTTPException(status_code=400, detail="Seleccione al menos un modulo")
        seleccion = [d for d in todos_dmps if d.id_detalle_programa_modulo in request.id_modulos]
        faltantes = set(request.id_modulos) - {d.id_detalle_programa_modulo for d in seleccion}
        if faltantes:
            raise HTTPException(status_code=400, detail=f"Modulos {sorted(faltantes)} no pertenecen a la edicion")

    id_dmps = [d.id_detalle_programa_modulo for d in seleccion]

    carreras_map = {None: {"id_carrera": None, "nombre": "Sin carrera"}}
    for c in db.query(Carrera).filter(Carrera.estado == "activo").all():
        carreras_map[c.id_carrera] = {"id_carrera": c.id_carrera, "nombre": c.nombre}

    dpas = db.query(DetalleProgramaAlumno).options(
        joinedload(DetalleProgramaAlumno.alumno)
    ).filter(
        DetalleProgramaAlumno.id_programa_version_edicion == request.id_programa_version_edicion,
        DetalleProgramaAlumno.estado.in_(ESTADOS_INCLUIDOS),
    ).all()
    if not dpas:
        raise HTTPException(status_code=400, detail="La edicion no tiene alumnos inscritos")

    dpa_ids = [d.id_detalle_programa_alumno for d in dpas]
    nota_map = {}
    if id_dmps:
        for n in db.query(Nota).filter(
            Nota.id_detalle_programa_alumno.in_(dpa_ids),
            Nota.id_detalle_programa_modulo.in_(id_dmps),
        ).all():
            nota_map[(n.id_detalle_programa_alumno, n.id_detalle_programa_modulo)] = float(n.nota)

    elegibilidad = calcular_elegibilidad(db, request.id_programa_version_edicion, dpas, nota_map, id_dmps)

    grupos = {}
    for d in dpas:
        key = d.id_carrera if d.id_carrera in carreras_map else None
        grupos.setdefault(key, []).append(d)

    carreras_resultado = []
    for key, alumnos_grupo in grupos.items():
        id_carrera = carreras_map[key]["id_carrera"]
        if request.id_carrera is not None and id_carrera != request.id_carrera:
            continue
        alumnos_grupo.sort(key=lambda d: (d.alumno.apellido, d.alumno.nombre))

        matriz_columnas = [
            {
                "id_detalle_programa_modulo": dpm.id_detalle_programa_modulo,
                "nombre_modulo": _nombre_modulo(dpm),
                "sigla": dpm.modulo.sigla if dpm.modulo else "",
            }
            for dpm in seleccion
        ]
        matrices_ids = [c["id_detalle_programa_modulo"] for c in matriz_columnas]

        matriz_filas = []
        for d in alumnos_grupo:
            det = elegibilidad[d.id_detalle_programa_alumno]
            notas_col = [nota_map.get((d.id_detalle_programa_alumno, m)) for m in matrices_ids]
            matriz_filas.append({
                **_arreglar_alumno(d),
                "notas": notas_col,
                "promedio": det["promedio"],
                "aprobada": det["aprobada"],
                "elegible": det["elegible"],
                "estado": det["estado"],
            })

        carreras_resultado.append({
            "id_carrera": id_carrera,
            "nombre": carreras_map[key]["nombre"],
            "matriz_columnas": matriz_columnas,
            "matriz_filas": matriz_filas,
        })

    todas_notas = all(
        nota_map.get((d.id_detalle_programa_alumno, m)) is not None
        for d in dpas for m in id_dmps
    )
    edicion_finalizada = pve.estado == "finalizado"
    if es_final:
        if not edicion_finalizada:
            raise HTTPException(status_code=400, detail="Informe final: la edicion no esta finalizada")
        if not todas_notas:
            raise HTTPException(status_code=400, detail="Informe final: faltan notas por cargar")

    total_alumnos = 0
    aprobados = 0
    completos = 0
    resumen_carreras = []
    for g in carreras_resultado:
        filas = g["matriz_filas"]
        n = len(filas)
        ap = sum(1 for f in filas if f["aprobada"])
        com = sum(1 for f in filas if f["elegible"])
        total_alumnos += n
        aprobados += ap
        completos += com
        resumen_carreras.append({"id_carrera": g["id_carrera"], "nombre": g["nombre"], "alumnos": n, "completos": com})

    return {
        "tipo": request.tipo,
        "id_programa_version_edicion": request.id_programa_version_edicion,
        "edicion_desc": None,
        "programa_nombre": programa.nombre_programa if programa else "",
        "version": pv.version if pv else 0,
        "edicion": pve.edicion,
        "semestre": pve.semestre,
        "anio": pve.anio,
        "carreras": carreras_resultado,
        "todas_notas": todas_notas,
        "edicion_finalizada": edicion_finalizada,
        "resumen": {
            "total_alumnos": total_alumnos,
            "total_aprobados": aprobados,
            "total_reprobados": max(total_alumnos - aprobados, 0),
            "completos": completos,
            "carreras": resumen_carreras,
        },
    }


def datos_certificado(db: Session, id_edicion: int, id_alumno: int) -> dict | None:
    """Snapshot congelado del alumno en la edición para el certificado de notas."""
    pve, pv, programa = resolver_edicion(db, id_edicion)
    d = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_programa_version_edicion == id_edicion,
        DetalleProgramaAlumno.id_alumno == id_alumno,
    ).first()
    if not d:
        return None

    dmps = modulos_edicion(db, id_edicion)
    nota_map = {
        n.id_detalle_programa_modulo: float(n.nota)
        for n in db.query(Nota).filter(Nota.id_detalle_programa_alumno == d.id_detalle_programa_alumno).all()
    }

    modulos = []
    for dpm in dmps:
        nota = nota_map.get(dpm.id_detalle_programa_modulo)
        modulos.append({
            "nombre": _nombre_modulo(dpm),
            "sigla": dpm.modulo.sigla if dpm.modulo else "",
            "nota": nota,
            "aprobada": nota is not None and nota >= NOTA_APROBATORIA,
            "clasificacion": clasificar_nota(nota).value if nota is not None else None,
        })

    notas = [m["nota"] for m in modulos if m["nota"] is not None]
    return {
        "programa": programa.nombre_programa if programa else "",
        "version": pv.version if pv else 0,
        "edicion": pve.edicion,
        "semestre": pve.semestre,
        "anio": pve.anio,
        "modalidad": d.modalidad_academica.nombre_modalidad if d.modalidad_academica else None,
        "carrera": d.carrera.nombre if d.carrera else None,
        "estado_alumno": d.estado,
        "alumno": {
            "nombre": d.alumno.nombre,
            "apellido": d.alumno.apellido,
            "ci": d.alumno.ci,
        },
        "modulos": modulos,
        "promedio": redondear_nota(sum(notas) / len(notas)) if notas else None,
    }