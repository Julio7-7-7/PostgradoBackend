from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from dependencies import get_current_user, require_permiso
from models.tipo_programa import TipoPrograma
from models.modalidad_academica import ModalidadAcademica
from schemas.tipo_programa import TipoProgramaCreate, TipoProgramaUpdate, TipoProgramaResponse
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/tipos-programa",
    tags=["Tipos de Programa"],
    dependencies=[Depends(get_current_user)]
)

def _cargar_con_relations(query):
    return query.options(
        joinedload(TipoPrograma.modalidades),
    )

def _sincronizar(tipo: TipoPrograma, modalidades_ids: list[int], db: Session):
    if modalidades_ids is not None:
        modalidades = db.query(ModalidadAcademica).filter(
            ModalidadAcademica.id_modalidad_academica.in_(modalidades_ids)
        ).all()
        tipo.modalidades = modalidades
    db.commit()
    db.refresh(tipo)


@router.post("/", response_model=TipoProgramaResponse, status_code=201)
def crear(data: TipoProgramaCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_programa.crear"))):
    existente = db.query(TipoPrograma).filter(TipoPrograma.nombre == data.nombre).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un tipo de programa con ese nombre")

    modalidades_ids = data.modalidades

    nuevo = TipoPrograma(
        nombre=data.nombre,
        estado=data.estado,
        cupo_minimo=data.cupo_minimo,
        duracion_minima_meses=data.duracion_minima_meses,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    _sincronizar(nuevo, modalidades_ids, db)
    return nuevo


@router.get("/", response_model=list[TipoProgramaResponse])
def listar(db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_programa.ver"))):
    query = db.query(TipoPrograma)
    return _cargar_con_relations(query).all()


@router.get("/{id}", response_model=TipoProgramaResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_programa.ver"))):
    query = db.query(TipoPrograma).filter(TipoPrograma.id_tipo_programa == id)
    tipo = _cargar_con_relations(query).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="No encontrado")
    return tipo


@router.patch("/{id}", response_model=TipoProgramaResponse)
def editar(id: int, data: TipoProgramaUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("tipos_programa.editar"))):
    tipo = db.query(TipoPrograma).filter(TipoPrograma.id_tipo_programa == id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="No encontrado")

    if data.nombre and data.nombre != tipo.nombre:
        existente = db.query(TipoPrograma).filter(
            TipoPrograma.nombre == data.nombre,
            TipoPrograma.id_tipo_programa != id
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail="Ya existe un tipo de programa con ese nombre")

    for key, value in data.model_dump(exclude_unset=True).items():
        if key != "modalidades":
            setattr(tipo, key, value)

    db.commit()
    db.refresh(tipo)

    _sincronizar(tipo, data.modalidades, db)
    return tipo
