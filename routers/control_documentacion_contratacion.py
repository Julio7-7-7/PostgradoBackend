from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from database import get_db
from dependencies import get_current_user, require_permiso
from models.control_documentacion_contratacion import ControlDocumentacionContratacion
from models.contratacion_docente import ContratacionDocente
from models.etapa_contratacion import EtapaContratacion
from schemas.control_documentacion_contratacion import (
    ControlDocContratacionCreate,
    ControlDocContratacionUpdate,
    ControlDocContratacionResponse,
)
from schemas.auth import UserResponse
import uuid
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/doc-contratacion",
    tags=["Documentos Contratacion"],
    dependencies=[Depends(get_current_user)],
)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "media", "contratos_doc")


def _cargar_con_relations(query):
    return query.options(
        joinedload(ControlDocumentacionContratacion.requisito),
        joinedload(ControlDocumentacionContratacion.etapa),
    )


@router.get("/", response_model=list[ControlDocContratacionResponse])
def listar(
    contratacion_id: int | None = None,
    etapa_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("contrataciones.ver")),
):
    query = db.query(ControlDocumentacionContratacion)
    if contratacion_id:
        query = query.filter(ControlDocumentacionContratacion.id_contratacion == contratacion_id)
    if etapa_id:
        query = query.filter(ControlDocumentacionContratacion.id_etapa == etapa_id)
    return _cargar_con_relations(query.order_by(
        ControlDocumentacionContratacion.id_etapa.asc(),
        ControlDocumentacionContratacion.id_control_doc_contratacion.asc(),
    )).all()


@router.get("/{id}", response_model=ControlDocContratacionResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.ver"))):
    doc = _cargar_con_relations(db.query(ControlDocumentacionContratacion)).filter(
        ControlDocumentacionContratacion.id_control_doc_contratacion == id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc


@router.post("/inicializar/{id_contratacion}", response_model=list[ControlDocContratacionResponse], status_code=201)
def inicializar_documentos(id_contratacion: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.crear"))):
    contratacion = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_contratacion == id_contratacion
    ).first()
    if not contratacion:
        raise HTTPException(status_code=404, detail="Contratación no encontrada")

    existentes = db.query(ControlDocumentacionContratacion).filter(
        ControlDocumentacionContratacion.id_contratacion == id_contratacion
    ).count()
    if existentes > 0:
        raise HTTPException(status_code=400, detail="Ya existen documentos asociados a esta contratación")

    from models.detalle_programa_modulo import DetalleProgramaModulo
    from models.programa_version_edicion import ProgramaVersionEdicion
    from models.programa_version import ProgramaVersion

    detalle = db.query(DetalleProgramaModulo).filter(
        DetalleProgramaModulo.id_detalle_programa_modulo == contratacion.id_detalle_modulo
    ).first()
    if not detalle:
        raise HTTPException(status_code=400, detail="No se encontró el detalle del módulo")

    pv = db.query(ProgramaVersion).join(
        ProgramaVersionEdicion, ProgramaVersionEdicion.id_programa_version == ProgramaVersion.id_programa_version
    ).filter(ProgramaVersionEdicion.id_programa_version_edicion == detalle.id_programa_version_edicion).first()
    if not pv:
        raise HTTPException(status_code=400, detail="No se encontró la versión del programa")

    etapas = db.query(EtapaContratacion).filter(
        EtapaContratacion.id_tipo_programa == pv.programa.id_tipo_programa
    ).order_by(EtapaContratacion.orden.asc()).all()

    if not etapas:
        raise HTTPException(status_code=400, detail="No hay etapas configuradas para el tipo de programa de esta contratación")

    primera_etapa = etapas[0]
    contratacion.id_etapa_actual = primera_etapa.id_etapa

    docs_creados = []
    for etapa in etapas:
        requisitos_etapa = db.query(EtapaRequisito).filter(
            EtapaRequisito.id_etapa == etapa.id_etapa
        ).all()
        for req in requisitos_etapa:
            nuevo_doc = ControlDocumentacionContratacion(
                id_contratacion=id_contratacion,
                id_requisito=req.id_requisito,
                id_etapa=etapa.id_etapa,
                estado="pendiente",
            )
            db.add(nuevo_doc)
            docs_creados.append(nuevo_doc)

    contratacion.id_etapa_actual = primera_etapa.id_etapa
    db.commit()
    db.refresh(contratacion)

    return _cargar_con_relations(db.query(ControlDocumentacionContratacion)).filter(
        ControlDocumentacionContratacion.id_contratacion == id_contratacion
    ).all()


@router.post("/{id}/subir", response_model=ControlDocContratacionResponse, status_code=200)
async def subir_documento(id: int, archivo: UploadFile = File(...), db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.editar"))):
    doc = db.query(ControlDocumentacionContratacion).filter(
        ControlDocumentacionContratacion.id_control_doc_contratacion == id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    contratacion = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_contratacion == doc.id_contratacion
    ).first()
    if contratacion.estado in ("truncado", "formalizado"):
        raise HTTPException(status_code=400, detail="No se pueden subir documentos a una contratación truncada o formalizada")

    if contratacion.id_etapa_actual != doc.id_etapa:
        raise HTTPException(status_code=400, detail="Solo se pueden subir documentos de la etapa actual")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(archivo.filename)[1] if archivo.filename else ".pdf"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    content = await archivo.read()
    with open(filepath, "wb") as f:
        f.write(content)

    doc.url_documento = f"/media/contratos_doc/{filename}"
    doc.estado = "entregado"
    db.commit()
    db.refresh(doc)

    return _cargar_con_relations(db.query(ControlDocumentacionContratacion)).filter(
        ControlDocumentacionContratacion.id_control_doc_contratacion == id
    ).first()


@router.patch("/{id}", response_model=ControlDocContratacionResponse)
def actualizar_estado(id: int, data: ControlDocContratacionUpdate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.editar"))):
    doc = db.query(ControlDocumentacionContratacion).filter(
        ControlDocumentacionContratacion.id_control_doc_contratacion == id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(doc, key, value)
    db.commit()
    db.refresh(doc)

    return _cargar_con_relations(db.query(ControlDocumentacionContratacion)).filter(
        ControlDocumentacionContratacion.id_control_doc_contratacion == id
    ).first()


@router.post("/{id_contratacion}/avanzar-etapa", response_model=list[ControlDocContratacionResponse])
def avanzar_etapa(id_contratacion: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.editar"))):
    contratacion = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_contratacion == id_contratacion
    ).first()
    if not contratacion:
        raise HTTPException(status_code=404, detail="Contratación no encontrada")
    if contratacion.estado in ("truncado", "formalizado"):
        raise HTTPException(status_code=400, detail="No se puede avanzar una contratación truncada o formalizada")
    if not contratacion.id_etapa_actual:
        raise HTTPException(status_code=400, detail="La contratación no tiene etapa actual asignada")

    docs_etapa_actual = db.query(ControlDocumentacionContratacion).filter(
        ControlDocumentacionContratacion.id_contratacion == id_contratacion,
        ControlDocumentacionContratacion.id_etapa == contratacion.id_etapa_actual,
        ControlDocumentacionContratacion.estado != "aceptado",
    ).all()

    if docs_etapa_actual:
        raise HTTPException(
            status_code=400,
            detail=f"Hay {len(docs_etapa_actual)} documentos pendientes de revisión en la etapa actual",
        )

    etapa_actual = db.query(EtapaContratacion).filter(
        EtapaContratacion.id_etapa == contratacion.id_etapa_actual
    ).first()

    siguiente = db.query(EtapaContratacion).filter(
        EtapaContratacion.id_tipo_programa == etapa_actual.id_tipo_programa,
        EtapaContratacion.orden > etapa_actual.orden,
    ).order_by(EtapaContratacion.orden.asc()).first()

    if siguiente:
        contratacion.id_etapa_actual = siguiente.id_etapa
    else:
        contratacion.estado = "formalizado"

    db.commit()
    db.refresh(contratacion)

    return _cargar_con_relations(db.query(ControlDocumentacionContratacion)).filter(
        ControlDocumentacionContratacion.id_contratacion == id_contratacion
    ).all()
