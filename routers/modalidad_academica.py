from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from dependencies import get_current_user, require_permiso
from models.modalidad_academica import ModalidadAcademica
from models.requisito import Requisito
from schemas.modalidad_academica import ModalidadAcademicaCreate, ModalidadAcademicaUpdate, ModalidadAcademicaResponse
from schemas.auth import UserResponse

router = APIRouter(
    prefix="/modalidades-academicas",
    tags=["Modalidades Academicas"],
    dependencies=[Depends(get_current_user)]
)

def _cargar_con_relations(query):
    return query.options(
        joinedload(ModalidadAcademica.requisitos),
    )

def _sincronizar_requisitos(modalidad: ModalidadAcademica, requisitos_ids: list[int], db: Session):
    if requisitos_ids is not None:
        requisitos = db.query(Requisito).filter(
            Requisito.id_requisito.in_(requisitos_ids)
        ).all()
        modalidad.requisitos = requisitos


@router.post("/", response_model=ModalidadAcademicaResponse, status_code=201)
def crear(data: ModalidadAcademicaCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("modalidades_academicas.crear"))):
    existente = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.nombre_modalidad == data.nombre_modalidad
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una modalidad académica con ese nombre")

    nueva = ModalidadAcademica(
        nombre_modalidad=data.nombre_modalidad,
        descripcion=data.descripcion,
        requiere_titulo=data.requiere_titulo,
        estado=data.estado,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)

    _sincronizar_requisitos(nueva, data.requisitos, db)
    db.commit()

    return _cargar_con_relations(
        db.query(ModalidadAcademica).filter(ModalidadAcademica.id_modalidad_academica == nueva.id_modalidad_academica)
    ).first()


@router.get("/", response_model=list[ModalidadAcademicaResponse])
def listar(db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("modalidades_academicas.ver"))):
    return _cargar_con_relations(
        db.query(ModalidadAcademica)
    ).all()


@router.get("/{id}", response_model=ModalidadAcademicaResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("modalidades_academicas.ver"))):
    modalidad = _cargar_con_relations(
        db.query(ModalidadAcademica).filter(ModalidadAcademica.id_modalidad_academica == id)
    ).first()
    if not modalidad:
        raise HTTPException(status_code=404, detail="No encontrado")
    return modalidad


@router.patch("/{id}", response_model=ModalidadAcademicaResponse)
def editar(id: int, data: ModalidadAcademicaUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("modalidades_academicas.editar"))):
    modalidad = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.id_modalidad_academica == id
    ).first()
    if not modalidad:
        raise HTTPException(status_code=404, detail="No encontrado")

    for key, value in data.model_dump(exclude_unset=True, exclude={"requisitos"}).items():
        setattr(modalidad, key, value)

    _sincronizar_requisitos(modalidad, data.requisitos, db)

    db.commit()

    return _cargar_con_relations(
        db.query(ModalidadAcademica).filter(ModalidadAcademica.id_modalidad_academica == id)
    ).first()


@router.delete("/{id}", status_code=204)
def eliminar(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("modalidades_academicas.editar"))):
    modalidad = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.id_modalidad_academica == id
    ).first()
    if not modalidad:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(modalidad)
    db.commit()
