from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models.contratacion_docente import ContratacionDocente
from models.docente import Docente
from models.detalle_programa_modulo import DetalleProgramaModulo
from schemas.contrataciones_docente import (
    ContratacionDocenteCreate,
    ContratacionDocenteUpdate,
    ContratacionDocenteResponse,
)

router = APIRouter(
    prefix="/contratacion-docente",
    tags=["Contratacion Docente"],
)


def query_base(db):
    return db.query(ContratacionDocente).options(
        joinedload(ContratacionDocente.docente),
        joinedload(ContratacionDocente.detalle_modulo),
    )


@router.post("/", response_model=ContratacionDocenteResponse, status_code=201)
def crear(data: ContratacionDocenteCreate, db: Session = Depends(get_db)):
    if not db.query(Docente).filter(Docente.id_docente == data.id_docente).first():
        raise HTTPException(status_code=400, detail="El docente especificado no existe")
    if not db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == data.id_detalle_modulo
    ).first():
        raise HTTPException(status_code=400, detail="El detalle de módulo especificado no existe")

    activa = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_detalle_modulo == data.id_detalle_modulo,
        ContratacionDocente.estado != "truncado",
    ).first()
    if activa:
        raise HTTPException(
            status_code=400,
            detail="Ya existe una contratación activa para este módulo. Trúncala antes de crear una nueva.",
        )

    nuevo = ContratacionDocente(**data.model_dump())
    detalle = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == data.id_detalle_modulo
    ).first()
    if detalle:
        nuevo.fecha_inicio = detalle.fecha_inicio
        nuevo.fecha_fin = detalle.fecha_fin
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return query_base(db).filter(
        ContratacionDocente.id_contratacion == nuevo.id_contratacion
    ).first()


@router.get("/", response_model=list[ContratacionDocenteResponse])
def listar(
    docente_id: int | None = None,
    detalle_id: int | None = None,
    estado: str | None = None,
    db: Session = Depends(get_db),
):
    query = query_base(db)
    if docente_id:
        query = query.filter(ContratacionDocente.id_docente == docente_id)
    if detalle_id:
        query = query.filter(ContratacionDocente.id_detalle_modulo == detalle_id)
    if estado:
        query = query.filter(ContratacionDocente.estado == estado)
    return query.all()


@router.get("/{id}", response_model=ContratacionDocenteResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    contratacion = query_base(db).filter(
        ContratacionDocente.id_contratacion == id
    ).first()
    if not contratacion:
        raise HTTPException(status_code=404, detail="Contratación no encontrada")
    return contratacion


@router.patch("/{id}", response_model=ContratacionDocenteResponse)
def editar(id: int, data: ContratacionDocenteUpdate, db: Session = Depends(get_db)):
    contratacion = query_base(db).filter(
        ContratacionDocente.id_contratacion == id
    ).first()
    if not contratacion:
        raise HTTPException(status_code=404, detail="Contratación no encontrada")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(contratacion, key, value)

    db.commit()
    db.refresh(contratacion)
    return query_base(db).filter(
        ContratacionDocente.id_contratacion == id
    ).first()


@router.patch("/{id}/truncar", response_model=ContratacionDocenteResponse)
def truncar(id: int, db: Session = Depends(get_db)):
    contratacion = query_base(db).filter(
        ContratacionDocente.id_contratacion == id
    ).first()
    if not contratacion:
        raise HTTPException(status_code=404, detail="Contratación no encontrada")
    if contratacion.estado == "truncado":
        raise HTTPException(status_code=400, detail="La contratación ya está truncada")
    if contratacion.estado == "formalizado":
        raise HTTPException(
            status_code=400,
            detail="No se puede truncar una contratación formalizada",
        )
    contratacion.estado = "truncado"
    db.commit()
    db.refresh(contratacion)
    return query_base(db).filter(
        ContratacionDocente.id_contratacion == id
    ).first()
