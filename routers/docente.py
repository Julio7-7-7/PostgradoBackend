from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db
from models.docente import Docente
from models.detalle_programa_modulo import DetalleProgramaModulo
from schemas.docente import DocenteCreate, DocenteUpdate, DocenteResponse

router = APIRouter(
    prefix="/docentes",
    tags=["Docentes"]
)

@router.post("/", response_model=DocenteResponse, status_code=201)
def crear(data: DocenteCreate, db: Session = Depends(get_db)):
    existente = db.query(Docente).filter(
        (Docente.ci == data.ci) | (Docente.correo == data.correo)
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un docente con ese CI o correo")
    nuevo = Docente(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.get("/", response_model=list[DocenteResponse])
def listar(estado: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Docente)
    if estado:
        query = query.filter(Docente.estado == estado)
    return query.all()

@router.get("/{id}", response_model=DocenteResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    docente = db.query(Docente).filter(Docente.id_docente == id).first()
    if not docente:
        raise HTTPException(status_code=404, detail="No encontrado")
    return docente

@router.patch("/{id}", response_model=DocenteResponse)
def editar(id: int, data: DocenteUpdate, db: Session = Depends(get_db)):
    docente = db.query(Docente).filter(Docente.id_docente == id).first()
    if not docente:
        raise HTTPException(status_code=404, detail="No encontrado")
    cambios = data.model_dump(exclude_unset=True)
    if "ci" in cambios or "correo" in cambios:
        filtros = []
        if "ci" in cambios:
            filtros.append(Docente.ci == cambios["ci"])
        if "correo" in cambios:
            filtros.append(Docente.correo == cambios["correo"])
        existente = db.query(Docente).filter(
            or_(*filtros), Docente.id_docente != id
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail="Ya existe otro docente con ese CI o correo")
    for key, value in cambios.items():
        setattr(docente, key, value)
    db.commit()
    db.refresh(docente)
    return docente

@router.patch("/{id}/cancelar", response_model=DocenteResponse)
def cancelar(id: int, db: Session = Depends(get_db)):
    docente = db.query(Docente).filter(Docente.id_docente == id).first()
    if not docente:
        raise HTTPException(status_code=404, detail="No encontrado")
    if docente.estado == "inactivo":
        raise HTTPException(status_code=400, detail="El docente ya está inactivo")
    modulos_activos = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_docente == id,
        DetalleProgramaModulo.estado != "finalizado"
    ).first()
    if modulos_activos:
        raise HTTPException(
            status_code=400,
            detail="No se puede dar de baja al docente porque tiene módulos activos asignados (no finalizados)"
        )
    docente.estado = "inactivo"
    db.commit()
    db.refresh(docente)
    return docente