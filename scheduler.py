from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.historial_modulo import HistorialModulo
from models.programa_version_edicion import ProgramaVersionEdicion

MOTIVO_AUTO_EN_CURSO = "Cambiado a estado en curso por fechas"
MOTIVO_AUTO_FINALIZADO = "Cambiado a estado finalizado por fecha de fin"

scheduler = BackgroundScheduler()


def auto_actualizar_estados():
    db = SessionLocal()
    try:
        detalles = db.query(DetalleProgramaModulo).all()
        cambios = 0
        hoy = date.today()

        for d in detalles:
            if d.estado == "programado" and d.fecha_inicio and d.fecha_inicio <= hoy:
                d.estado = "en_curso"
                db.add(HistorialModulo(
                    id_detalle_programa_modulo=d.id_detalle_programa_modulo,
                    estado_anterior="programado",
                    estado_nuevo="en_curso",
                    motivo=MOTIVO_AUTO_EN_CURSO,
                    fecha_inicio_original=d.fecha_inicio,
                    fecha_fin_original=d.fecha_fin,
                ))
                cambios += 1

            elif d.estado == "reprogramado" and d.fecha_inicio and d.fecha_inicio <= hoy:
                d.estado = "en_curso"
                db.add(HistorialModulo(
                    id_detalle_programa_modulo=d.id_detalle_programa_modulo,
                    estado_anterior="reprogramado",
                    estado_nuevo="en_curso",
                    motivo=MOTIVO_AUTO_EN_CURSO,
                    fecha_inicio_original=d.fecha_inicio,
                    fecha_fin_original=d.fecha_fin,
                ))
                cambios += 1

            elif d.estado == "en_curso" and d.fecha_fin and d.fecha_fin < hoy:
                d.estado = "finalizado"
                db.add(HistorialModulo(
                    id_detalle_programa_modulo=d.id_detalle_programa_modulo,
                    estado_anterior="en_curso",
                    estado_nuevo="finalizado",
                    motivo=MOTIVO_AUTO_FINALIZADO,
                    fecha_inicio_original=d.fecha_inicio,
                    fecha_fin_original=d.fecha_fin,
                ))
                cambios += 1

        if cambios:
            db.commit()

        # Actualizar estado de ediciones según el estado de sus módulos
        ediciones_ids = set(d.id_programa_version_edicion for d in detalles)
        for eid in ediciones_ids:
            actualizar_estado_edicion(eid, db)
        db.commit()

    except Exception as e:
        print(f"[scheduler] Error en auto_actualizar_estados: {e}")
    finally:
        db.close()


def actualizar_estado_edicion(id_edicion: int, db) -> bool:
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


def iniciar():
    scheduler.add_job(
        auto_actualizar_estados,
        trigger="interval",
        hours=1,
        id="auto_estados_modulos",
        name="Auto actualizar estados de módulos según fechas",
        replace_existing=True,
    )
    scheduler.start()


def detener():
    scheduler.shutdown(wait=False)
