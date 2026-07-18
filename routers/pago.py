from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_permiso
from models.pago import Pago
from models.alumno import Alumno
from models.detalle_programa_alumno import DetalleProgramaAlumno
from schemas.pago import PagoCreate, PagoUpdate, PagoResponse
from schemas.auth import UserResponse
from routers.utils import eliminar_foto

router = APIRouter(
    prefix="/pagos",
    tags=["Pagos"],
    dependencies=[Depends(get_current_user)]
)


def _es_alumno_actual(usuario: UserResponse, id_alumno: int, db: Session) -> bool:
    if usuario.profile_type == "alumno" and usuario.id_profile == id_alumno:
        return True
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id_alumno).first()
    if not alumno or not alumno.id_usuario:
        return False
    return alumno.id_usuario == usuario.id_usuario


@router.get("/por-edicion/{id_edicion}")
def pagos_por_edicion(
    id_edicion: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver"))
):
    detalles = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_programa_version_edicion == id_edicion
    ).all()

    resultado = []
    for detalle in detalles:
        pagos = db.query(Pago).filter(
            Pago.id_detalle_programa_alumno == detalle.id_detalle_programa_alumno
        ).order_by(Pago.fecha_pago.desc()).all()

        alumno = db.query(Alumno).filter(Alumno.id_alumno == detalle.id_alumno).first()

        total_pagado = sum(float(p.monto) for p in pagos if p.estado == "confirmado")

        resultado.append({
            "id_detalle_programa_alumno": detalle.id_detalle_programa_alumno,
            "alumno": {
                "id_alumno": alumno.id_alumno if alumno else None,
                "nombre": alumno.nombre if alumno else "N/A",
                "apellido": alumno.apellido if alumno else "N/A",
                "ci": alumno.ci if alumno else None,
            } if alumno else None,
            "descuento_aplicado": float(detalle.descuento_aplicado) if detalle.descuento_aplicado else 0,
            "pagos": [
                {
                    "id_pago": p.id_pago,
                    "monto": float(p.monto),
                    "fecha_pago": str(p.fecha_pago),
                    "concepto": p.concepto,
                    "comprobante_url": p.comprobante_url,
                    "numero_referencia": p.numero_referencia,
                    "estado": p.estado,
                    "observaciones": p.observaciones,
                    "created_at": str(p.created_at),
                    "updated_at": str(p.updated_at),
                }
                for p in pagos
            ],
            "total_pagado": total_pagado,
        })

    return resultado


@router.get("/mis-pagos/{id_detalle}")
def mis_pagos(
    id_detalle: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.profile_type != "alumno" or not current_user.id_profile:
        raise HTTPException(status_code=400, detail="El usuario actual no es un alumno")

    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == id_detalle,
        DetalleProgramaAlumno.id_alumno == current_user.id_profile,
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    pagos = db.query(Pago).filter(
        Pago.id_detalle_programa_alumno == id_detalle
    ).order_by(Pago.fecha_pago.desc()).all()

    total_pagado = sum(float(p.monto) for p in pagos if p.estado == "confirmado")

    return {
        "pagos": pagos,
        "total_pagado": total_pagado,
    }


@router.post("/", response_model=PagoResponse, status_code=201)
def crear_pago(data: PagoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("pagos.registrar"))):
    detalle = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == data.id_detalle_programa_alumno
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    if float(data.monto) <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")

    if _es_alumno_actual(current_user, detalle.id_alumno, db):
        raise HTTPException(status_code=403, detail="No podés registrar pagos para tu propia inscripción")

    nuevo = Pago(**data.model_dump())
    db.add(nuevo)
    db.flush()
    db.refresh(nuevo)
    return nuevo


@router.patch("/{id}", response_model=PagoResponse)
def editar_pago(
    id: int,
    data: PagoUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.registrar"))
):
    pago = db.query(Pago).filter(Pago.id_pago == id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    detalle_pago = db.query(DetalleProgramaAlumno).filter(
        DetalleProgramaAlumno.id_detalle_programa_alumno == pago.id_detalle_programa_alumno
    ).first()
    if detalle_pago and _es_alumno_actual(current_user, detalle_pago.id_alumno, db):
        raise HTTPException(status_code=403, detail="No podés modificar pagos de tu propia inscripción")

    if data.monto is not None and float(data.monto) <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")

    if data.comprobante_url and pago.comprobante_url:
        eliminar_foto(pago.comprobante_url)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(pago, key, value)
    db.flush()
    db.refresh(pago)
    return pago


@router.get("/{id}", response_model=PagoResponse)
def obtener_pago(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("pagos.ver"))
):
    pago = db.query(Pago).filter(Pago.id_pago == id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return pago
