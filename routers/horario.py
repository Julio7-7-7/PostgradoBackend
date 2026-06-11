from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from database import get_db
from models.horario import Horario
from models.detalle_programa_modulo import DetalleProgramaModulo
from schemas.horario import HorarioCreate, HorarioUpdate, HorarioResponse, HorarioListResponse

router = APIRouter(
    prefix="/horarios",
    tags=["Horarios"]
)

def query_detail(db):
    return db.query(Horario).options(
        joinedload(Horario.detalle_programa_modulo)
        .joinedload(DetalleProgramaModulo.modulo),
        joinedload(Horario.detalle_programa_modulo)
        .joinedload(DetalleProgramaModulo.docente),
        joinedload(Horario.detalle_programa_modulo)
        .joinedload(DetalleProgramaModulo.modalidad),
    )

def verificar_solapamiento(db, id_detalle, dia, hora_ini, hora_fin, excluir_id=None):
    query = db.query(Horario).filter(
        Horario.id_detalle_programa_modulo == id_detalle,
        Horario.dia == dia,
        Horario.estado != "cancelado",
        Horario.hora_ini < hora_fin,
        Horario.hora_fin > hora_ini
    )
    if excluir_id:
        query = query.filter(Horario.id_horario != excluir_id)
    if query.first():
        raise HTTPException(status_code=400, detail="El horario se solapa con otro horario existente en este módulo")

def verificar_docente(db: Session, id_detalle: int, dia: str, hora_ini, hora_fin, excluir_id: int = None):
    detalle = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == id_detalle
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle de módulo no encontrado")

    if detalle.id_docente is None:
        return

    choque = db.query(Horario).join(
        DetalleProgramaModulo,
        Horario.id_detalle_programa_modulo == DetalleProgramaModulo.id_detalle_programa_modulo
    ).filter(
        DetalleProgramaModulo.id_docente == detalle.id_docente,
        DetalleProgramaModulo.estado.in_(["programado", "en_curso"]),
        Horario.estado != "cancelado",
        Horario.dia == dia,
        Horario.hora_ini < hora_fin,
        Horario.hora_fin > hora_ini
    )

    if excluir_id:
        choque = choque.filter(Horario.id_horario != excluir_id)

    conflicto = choque.first()
    if conflicto:
        raise HTTPException(
            status_code=400,
            detail=f"Conflicto de agenda: el docente ya tiene clase el {dia} de {conflicto.hora_ini} a {conflicto.hora_fin}"
        )

@router.post("/", response_model=HorarioResponse, status_code=201)
def crear(data: HorarioCreate, db: Session = Depends(get_db)):
    verificar_solapamiento(db, data.id_detalle_programa_modulo, data.dia, data.hora_ini, data.hora_fin)
    verificar_docente(db, data.id_detalle_programa_modulo, data.dia, data.hora_ini, data.hora_fin)
    nuevo = Horario(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return query_detail(db).filter(Horario.id_horario == nuevo.id_horario).first()

@router.get("/", response_model=list[HorarioListResponse])
def listar(detalle_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Horario)
    if detalle_id:
        query = query.filter(Horario.id_detalle_programa_modulo == detalle_id)
    return query.all()

@router.get("/{id}", response_model=HorarioResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    horario = query_detail(db).filter(Horario.id_horario == id).first()
    if not horario:
        raise HTTPException(status_code=404, detail="No encontrado")
    return horario

@router.patch("/{id}", response_model=HorarioResponse)
def editar(id: int, data: HorarioUpdate, db: Session = Depends(get_db)):
    horario = query_detail(db).filter(Horario.id_horario == id).first()
    if not horario:
        raise HTTPException(status_code=404, detail="No encontrado")
    hora_ini = data.hora_ini or horario.hora_ini
    hora_fin = data.hora_fin or horario.hora_fin
    dia = data.dia or horario.dia
    verificar_solapamiento(db, horario.id_detalle_programa_modulo, dia, hora_ini, hora_fin, excluir_id=id)
    verificar_docente(db, horario.id_detalle_programa_modulo, dia, hora_ini, hora_fin, excluir_id=id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(horario, key, value)
    db.commit()
    db.refresh(horario)
    return query_detail(db).filter(Horario.id_horario == id).first()

@router.patch("/{id}/cancelar", response_model=HorarioResponse)
def cancelar(id: int, db: Session = Depends(get_db)):
    horario = query_detail(db).filter(Horario.id_horario == id).first()
    if not horario:
        raise HTTPException(status_code=404, detail="No encontrado")
    if horario.estado == "cancelado":
        raise HTTPException(status_code=400, detail="El horario ya está cancelado")
    horario.estado = "cancelado"
    db.commit()
    db.refresh(horario)
    return horario
