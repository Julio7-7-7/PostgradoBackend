from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal
from models.detalle_programa_modulo import DetalleProgramaModulo
from models.historial_modulo import HistorialModulo

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

    except Exception as e:
        print(f"[scheduler] Error en auto_actualizar_estados: {e}")
    finally:
        db.close()


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
