from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db
from models.docente import Docente
from models.contratacion_docente import ContratacionDocente
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
    resp = DocenteResponse.model_validate(nuevo)
    resp.tiene_modulos_activos = False
    return resp

def _ids_con_contratos(db: Session) -> set[int]:
    filas = db.query(ContratacionDocente.id_docente).filter(
        ContratacionDocente.estado != "truncado",
    ).distinct().all()
    return {r[0] for r in filas}

@router.get("/", response_model=list[DocenteResponse])
def listar(estado: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Docente)
    if estado:
        query = query.filter(Docente.estado == estado)
    docentes = query.all()
    ids_con_contratos = _ids_con_contratos(db)
    respuestas = []
    for d in docentes:
        r = DocenteResponse.model_validate(d)
        r.tiene_modulos_activos = d.id_docente in ids_con_contratos
        respuestas.append(r)
    return respuestas

@router.get("/{id}", response_model=DocenteResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    docente = db.query(Docente).filter(Docente.id_docente == id).first()
    if not docente:
        raise HTTPException(status_code=404, detail="No encontrado")
    resp = DocenteResponse.model_validate(docente)
    resp.tiene_modulos_activos = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_docente == id,
        ContratacionDocente.estado != "truncado",
    ).first() is not None
    return resp

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
    resp = DocenteResponse.model_validate(docente)
    resp.tiene_modulos_activos = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_docente == id,
        ContratacionDocente.estado != "truncado",
    ).first() is not None
    return resp

@router.patch("/{id}/cancelar", response_model=DocenteResponse)
def cancelar(id: int, db: Session = Depends(get_db)):
    docente = db.query(Docente).filter(Docente.id_docente == id).first()
    if not docente:
        raise HTTPException(status_code=404, detail="No encontrado")
    if docente.estado == "inactivo":
        raise HTTPException(status_code=400, detail="El docente ya está inactivo")
    contratos_activos = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_docente == id,
        ContratacionDocente.estado != "truncado",
    ).first()
    if contratos_activos:
        raise HTTPException(
            status_code=400,
            detail="No se puede dar de baja al docente porque tiene contrataciones activas"
        )
    docente.estado = "inactivo"
    db.commit()
    db.refresh(docente)
    resp = DocenteResponse.model_validate(docente)
    resp.tiene_modulos_activos = False
    return resp
