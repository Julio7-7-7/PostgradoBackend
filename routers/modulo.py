from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from database import get_db
from models.modulo import Modulo
from models.programa_version_edicion import ProgramaVersionEdicion
from models.programa_version import ProgramaVersion
from schemas.modulo import ModuloCreate, ModuloUpdate, ModuloResponse

router = APIRouter(
    prefix="/modulos",
    tags=["Modulos"]
)

@router.post("/", response_model=ModuloResponse, status_code=201)
def crear(data: ModuloCreate, db: Session = Depends(get_db)):
    pv = db.query(ProgramaVersion).filter(
        ProgramaVersion.id_programa_version == data.id_programa_version
    ).first()
    if pv and not pv.es_historico:
        ediciones = db.query(ProgramaVersionEdicion).filter(
            ProgramaVersionEdicion.id_programa_version == data.id_programa_version
        ).count()
        if ediciones > 0:
            raise HTTPException(
                status_code=400,
                detail="Esta versión ya cuenta con ediciones registradas. Para mantener la consistencia del programa, no es posible añadir nuevos módulos."
            )

    existente = db.query(Modulo).filter(Modulo.sigla == data.sigla).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un módulo con esa sigla")

    try:
        nuevo = Modulo(**data.model_dump())
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return nuevo
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Conflicto: ocurrió un error al crear el módulo. Verifique que la sigla no esté duplicada."
        )

@router.get("/", response_model=list[ModuloResponse])
def listar(programa_version_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Modulo).options(joinedload(Modulo.programa_version))
    if programa_version_id:
        query = query.filter(Modulo.id_programa_version == programa_version_id)
    return query.all()

@router.get("/{id}", response_model=ModuloResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    modulo = db.query(Modulo).options(joinedload(Modulo.programa_version)).filter(Modulo.id_modulo == id).first()
    if not modulo:
        raise HTTPException(status_code=404, detail="No encontrado")
    return modulo

@router.patch("/{id}", response_model=ModuloResponse)
def editar(id: int, data: ModuloUpdate, db: Session = Depends(get_db)):
    modulo = db.query(Modulo).options(joinedload(Modulo.programa_version)).filter(Modulo.id_modulo == id).first()
    if not modulo:
        raise HTTPException(status_code=404, detail="No encontrado")

    if data.estado == "inactivo":
        pv = db.query(ProgramaVersion).filter(
            ProgramaVersion.id_programa_version == modulo.id_programa_version
        ).first()
        if pv and not pv.es_historico:
            ediciones = db.query(ProgramaVersionEdicion).filter(
                ProgramaVersionEdicion.id_programa_version == modulo.id_programa_version
            ).count()
            if ediciones > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Esta versión tiene ediciones registradas, por lo que no es posible desactivar módulos del plan de estudios."
                )

    if data.sigla and data.sigla != modulo.sigla:
        existente = db.query(Modulo).filter(
            Modulo.sigla == data.sigla,
            Modulo.id_modulo != id
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail="Ya existe otro módulo con esa sigla")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(modulo, key, value)

    try:
        db.commit()
        modulo = db.query(Modulo).options(joinedload(Modulo.programa_version)).filter(Modulo.id_modulo == id).first()
        return modulo
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Conflicto: ocurrió un error al actualizar el módulo."
        )
