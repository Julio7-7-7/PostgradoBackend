from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, not_
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.historial_modulo import HistorialModulo
from models.contratacion_docente import ContratacionDocente
from models.modulo import Modulo
from models.programa_version import ProgramaVersion
from models.programa_version_edicion import ProgramaVersionEdicion
from schemas.detalle_programa_modulo import DetalleProgramaModuloCreate, DetalleProgramaModuloUpdate, DetalleProgramaModuloResponse, ReordenarRequest
from schemas.contrataciones_docente import ContratacionDocenteResponse

router = APIRouter(
    prefix="/detalle-programa-modulo",
    tags=["Detalle Programa Modulo"]
)

DURACION_MINIMA_DIAS = 30

ESTADOS_CON_MOTIVO = {"reprogramado"}
MOTIVO_AUTO_EN_CURSO = "Cambiado a estado en curso por fechas"
MOTIVO_AUTO_FINALIZADO = "Cambiado a estado finalizado por fecha de fin"

ESTADO_TRANSICIONES = {
    "programado": {"en_curso"},
    "en_curso": {"reprogramado", "finalizado"},
    "reprogramado": {"en_curso"},
    "finalizado": set(),
}

def validar_transicion(estado_actual: str, estado_nuevo: str):
    permitidos = ESTADO_TRANSICIONES.get(estado_actual, set())
    if estado_nuevo not in permitidos:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se puede cambiar de '{estado_actual}' a '{estado_nuevo}'. "
                f"Transiciones permitidas: {', '.join(sorted(permitidos)) if permitidos else 'ninguna'}"
            )
        )

def query_base(db):
    return db.query(DetalleProgramaModulo).options(
        joinedload(DetalleProgramaModulo.modulo),
        joinedload(DetalleProgramaModulo.contrataciones).joinedload(ContratacionDocente.docente),
        joinedload(DetalleProgramaModulo.programa_version_edicion)
            .joinedload(ProgramaVersionEdicion.programa_version)
            .joinedload(ProgramaVersion.programa),
    )

def poblar_docente_y_contratacion(detalles: list[DetalleProgramaModulo] | DetalleProgramaModulo):
    lista = detalles if isinstance(detalles, list) else [detalles]
    for d in lista:
        d.docente = None
        d.contratacion = None
        for c in d.contrataciones:
            if c.estado != "truncado":
                d.docente = c.docente
                d.contratacion = c
                break

def actualizar_estado_auto(detalle: DetalleProgramaModulo, db: Session) -> bool:
    hoy = date.today()

    if detalle.estado == "programado" and detalle.fecha_inicio and detalle.fecha_inicio <= hoy:
        detalle.estado = "en_curso"
        historial = HistorialModulo(
            id_detalle_programa_modulo=detalle.id_detalle_programa_modulo,
            estado_anterior="programado",
            estado_nuevo="en_curso",
            motivo=MOTIVO_AUTO_EN_CURSO,
            fecha_inicio_original=detalle.fecha_inicio,
            fecha_inicio_nuevo=detalle.fecha_inicio,
            fecha_fin_original=detalle.fecha_fin,
            fecha_fin_nuevo=detalle.fecha_fin,
        )
        db.add(historial)
        actualizar_estado_edicion(detalle.id_programa_version_edicion, db)
        return True

    if detalle.estado == "reprogramado" and detalle.fecha_inicio and detalle.fecha_inicio <= hoy:
        detalle.estado = "en_curso"
        historial = HistorialModulo(
            id_detalle_programa_modulo=detalle.id_detalle_programa_modulo,
            estado_anterior="reprogramado",
            estado_nuevo="en_curso",
            motivo=MOTIVO_AUTO_EN_CURSO,
            fecha_inicio_original=detalle.fecha_inicio,
            fecha_inicio_nuevo=detalle.fecha_inicio,
            fecha_fin_original=detalle.fecha_fin,
            fecha_fin_nuevo=detalle.fecha_fin,
        )
        db.add(historial)
        actualizar_estado_edicion(detalle.id_programa_version_edicion, db)
        return True

    if detalle.estado == "en_curso" and detalle.fecha_fin and detalle.fecha_fin < hoy:
        detalle.estado = "finalizado"
        historial = HistorialModulo(
            id_detalle_programa_modulo=detalle.id_detalle_programa_modulo,
            estado_anterior="en_curso",
            estado_nuevo="finalizado",
            motivo=MOTIVO_AUTO_FINALIZADO,
            fecha_inicio_original=detalle.fecha_inicio,
            fecha_inicio_nuevo=detalle.fecha_inicio,
            fecha_fin_original=detalle.fecha_fin,
            fecha_fin_nuevo=detalle.fecha_fin,
        )
        db.add(historial)
        actualizar_estado_edicion(detalle.id_programa_version_edicion, db)
        return True

    return False

def actualizar_estado_edicion(id_edicion: int, db: Session) -> bool:
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

@router.post("/", response_model=DetalleProgramaModuloResponse, status_code=201)
def crear(data: DetalleProgramaModuloCreate, db: Session = Depends(get_db)):
    if not db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == data.id_programa_version_edicion
    ).first():
        raise HTTPException(status_code=400, detail="La edición especificada no existe")
    if not db.query(Modulo).filter(Modulo.id_modulo == data.id_modulo).first():
        raise HTTPException(status_code=400, detail="El módulo especificado no existe")
    orden_existente = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == data.id_programa_version_edicion,
        DetalleProgramaModulo.orden == data.orden
    ).first()
    if orden_existente:
        raise HTTPException(status_code=400, detail=f"Ya existe un módulo con orden {data.orden} en esta edición")
    nuevo = DetalleProgramaModulo(**data.model_dump())
    db.add(nuevo)
    db.flush()
    actualizar_estado_auto(nuevo, db)
    db.commit()
    db.refresh(nuevo)
    detalle = query_base(db).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == nuevo.id_detalle_programa_modulo
    ).first()
    poblar_docente_y_contratacion(detalle)
    return detalle

@router.post("/reordenar", status_code=200)
def reordenar(data: ReordenarRequest, db: Session = Depends(get_db)):
    ids_recibidos = {item.id_detalle for item in data.ordenes}
    ordenes_recibidos = [item.orden for item in data.ordenes]
    esperados = set(range(1, len(data.ordenes) + 1))

    if set(ordenes_recibidos) != esperados:
        raise HTTPException(status_code=400, detail="Los órdenes deben ser 1..N sin repetir")

    existentes = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_programa_version_edicion == data.id_edicion
    ).all()

    ids_reales = {d.id_detalle_programa_modulo for d in existentes}
    if ids_recibidos != ids_reales:
        raise HTTPException(status_code=400, detail="Los módulos enviados no coinciden con los de la edición")

    for d in existentes:
        actualizar_estado_auto(d, db)
        if d.estado == "finalizado":
            raise HTTPException(status_code=400, detail="No se puede reordenar: hay módulos finalizados en la edición")

    for item in data.ordenes:
        db.query(DetalleProgramaModulo).filter(
            DetalleProgramaModulo.id_detalle_programa_modulo == item.id_detalle
        ).update({"orden": -item.orden})

    db.flush()

    for item in data.ordenes:
        db.query(DetalleProgramaModulo).filter(
            DetalleProgramaModulo.id_detalle_programa_modulo == item.id_detalle
        ).update({"orden": item.orden})

    db.commit()

    return {"mensaje": "Orden actualizado correctamente"}


@router.get("/", response_model=list[DetalleProgramaModuloResponse])
def listar(
    edicion_id: int | None = None,
    id_docente: int | None = None,
    programa_id: int | None = None,
    disponible: bool | None = None,
    db: Session = Depends(get_db),
):
    query = query_base(db)
    if edicion_id:
        query = query.filter(DetalleProgramaModulo.id_programa_version_edicion == edicion_id)
    if id_docente:
        subq = select(ContratacionDocente.id_detalle_modulo).where(
            ContratacionDocente.id_docente == id_docente,
            ContratacionDocente.estado != "truncado",
        )
        query = query.filter(DetalleProgramaModulo.id_detalle_programa_modulo.in_(subq))
    if programa_id:
        query = (
            query
            .join(DetalleProgramaModulo.programa_version_edicion)
            .join(ProgramaVersionEdicion.programa_version)
            .filter(ProgramaVersion.id_programa == programa_id)
        )
    if disponible:
        subq_activa = select(ContratacionDocente.id_detalle_modulo).where(
            ContratacionDocente.estado != "truncado",
        )
        query = query.filter(
            not_(DetalleProgramaModulo.id_detalle_programa_modulo.in_(subq_activa))
        )
    resultados = query.all()
    cambios = False
    for d in resultados:
        if actualizar_estado_auto(d, db):
            cambios = True
    if cambios:
        db.commit()
        resultados = query.all()
    poblar_docente_y_contratacion(resultados)
    return resultados

@router.get("/{id}", response_model=DetalleProgramaModuloResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    detalle = query_base(db).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == id
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="No encontrado")
    if actualizar_estado_auto(detalle, db):
        db.commit()
        detalle = query_base(db).filter(
            DetalleProgramaModulo.id_detalle_programa_modulo == id
        ).first()
    poblar_docente_y_contratacion(detalle)
    return detalle

@router.patch("/{id}", response_model=DetalleProgramaModuloResponse)
def editar(id: int, data: DetalleProgramaModuloUpdate, db: Session = Depends(get_db)):
    detalle = query_base(db).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == id
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="No encontrado")

    estado_solicitado = data.estado
    fecha_inicio = data.fecha_inicio
    fecha_fin = data.fecha_fin

    estado_changed = estado_solicitado is not None and estado_solicitado != detalle.estado

    # Auto-fechas al pasar a en_curso
    if estado_solicitado == "en_curso" and estado_changed:
        if fecha_inicio is None:
            fecha_inicio = date.today()
        if fecha_fin is None:
            fecha_fin = fecha_inicio + timedelta(days=DURACION_MINIMA_DIAS)

    inicio_changed = fecha_inicio is not None and fecha_inicio != detalle.fecha_inicio
    fin_changed = fecha_fin is not None and fecha_fin != detalle.fecha_fin

    # Auto reprogramado al modificar fechas de un módulo en curso
    if detalle.estado == "en_curso" and not estado_changed and (inicio_changed or fin_changed):
        estado_solicitado = "reprogramado"
        estado_changed = True

    # Validar duración mínima si hay fechas
    if fecha_inicio and fecha_fin:
        diff = (fecha_fin - fecha_inicio).days
        if diff < DURACION_MINIMA_DIAS:
            raise HTTPException(
                status_code=400,
                detail=f"La duración mínima del módulo es de {DURACION_MINIMA_DIAS} días (actual: {diff})"
            )

    # Validar que las fechas del módulo estén dentro del rango de la edición
    edicion = db.query(ProgramaVersionEdicion).filter(
        ProgramaVersionEdicion.id_programa_version_edicion == detalle.id_programa_version_edicion
    ).first()
    fecha_ini_mod = fecha_inicio if inicio_changed else detalle.fecha_inicio
    fecha_fin_mod = fecha_fin if fin_changed else detalle.fecha_fin
    if edicion and edicion.fecha_inicio and fecha_ini_mod and fecha_ini_mod < edicion.fecha_inicio:
        raise HTTPException(
            status_code=400,
            detail=f"La fecha de inicio del módulo ({fecha_ini_mod.strftime('%d/%m/%Y')}) no puede ser anterior a la fecha de inicio de la edición ({edicion.fecha_inicio.strftime('%d/%m/%Y')})"
        )
    if edicion and edicion.fecha_fin and fecha_fin_mod and fecha_fin_mod > edicion.fecha_fin:
        raise HTTPException(
            status_code=400,
            detail=f"La fecha de fin del módulo ({fecha_fin_mod.strftime('%d/%m/%Y')}) no puede ser posterior a la fecha de fin de la edición ({edicion.fecha_fin.strftime('%d/%m/%Y')})"
        )

    if estado_changed or inicio_changed or fin_changed:
        if estado_changed:
            validar_transicion(detalle.estado, estado_solicitado)

            if estado_solicitado in ESTADOS_CON_MOTIVO:
                if not data.motivo:
                    raise HTTPException(
                        status_code=400,
                        detail=f"El campo motivo es obligatorio cuando el estado es {estado_solicitado}"
                    )
                if len(data.motivo.strip()) < 5:
                    raise HTTPException(
                        status_code=400,
                        detail="El motivo debe tener al menos 5 caracteres"
                    )

        partes = []
        if estado_changed:
            partes.append(f"estado: '{detalle.estado}' → '{estado_solicitado}'")
        if inicio_changed:
            old_ini = detalle.fecha_inicio.strftime('%d/%m/%Y') if detalle.fecha_inicio else '—'
            partes.append(f"fecha inicio: {old_ini} → {fecha_inicio.strftime('%d/%m/%Y')}")
        if fin_changed:
            old_fin = detalle.fecha_fin.strftime('%d/%m/%Y') if detalle.fecha_fin else '—'
            partes.append(f"fecha fin: {old_fin} → {fecha_fin.strftime('%d/%m/%Y')}")

        if data.motivo:
            motivo = f"Cambio manual — {data.motivo.strip()}"
        elif estado_changed:
            motivo = f"Cambio manual — {', '.join(partes)}"
        else:
            motivo = "Modificación de " + ", ".join(partes)

        historial = HistorialModulo(
            id_detalle_programa_modulo=id,
            estado_anterior=detalle.estado if estado_changed else None,
            estado_nuevo=estado_solicitado if estado_changed else None,
            motivo=motivo,
            fecha_inicio_original=detalle.fecha_inicio if inicio_changed else None,
            fecha_inicio_nuevo=fecha_inicio if inicio_changed else None,
            fecha_fin_original=detalle.fecha_fin if fin_changed else None,
            fecha_fin_nuevo=fecha_fin if fin_changed else None,
        )
        db.add(historial)

        if estado_changed:
            detalle.estado = estado_solicitado
            actualizar_estado_edicion(detalle.id_programa_version_edicion, db)
        if inicio_changed:
            detalle.fecha_inicio = fecha_inicio
        if fin_changed:
            detalle.fecha_fin = fecha_fin

    if data.orden is not None:
        orden_existente = db.query(DetalleProgramaModulo).filter(
            DetalleProgramaModulo.id_programa_version_edicion == detalle.id_programa_version_edicion,
            DetalleProgramaModulo.orden == data.orden,
            DetalleProgramaModulo.id_detalle_programa_modulo != id
        ).first()
        if orden_existente:
            raise HTTPException(status_code=400, detail=f"Ya existe un módulo con orden {data.orden} en esta edición")
        detalle.orden = data.orden

    if data.modalidad is not None:
        detalle.modalidad = data.modalidad.value

    db.commit()
    detalle = query_base(db).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == id
    ).first()
    poblar_docente_y_contratacion(detalle)
    return detalle
