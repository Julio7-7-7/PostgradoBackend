import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session, joinedload
from database import get_db
from dependencies import get_current_user, require_permiso
from models.documento_contratacion import DocumentoContratacion
from models.contratacion_docente import ContratacionDocente
from schemas.documentos_contratacion import (
    DocumentoContratacionCreate,
    DocumentoContratacionResponse,
)
from schemas.auth import UserResponse
from routers.utils import guardar_pdf_base64

router = APIRouter(
    prefix="/documentos-contratacion",
    tags=["Documentos Contratacion"],
    dependencies=[Depends(get_current_user)]
)

GATILLOS_POR_POSICION = {
    0: "verificacion",
    3: "convocatoria",
    6: "seleccion",
    9: "resolucion",
    12: "legal",
    19: "formalizado",
}
MAX_DOCUMENTOS = 20


def query_base(db):
    return db.query(DocumentoContratacion).options(
        joinedload(DocumentoContratacion.contratacion),
    )


def _validar_contratacion_activa(contratacion: ContratacionDocente | None):
    if not contratacion:
        raise HTTPException(status_code=400, detail="La contratación especificada no existe")
    if contratacion.estado == "truncado":
        raise HTTPException(status_code=400, detail="No se pueden agregar documentos a una contratación truncada")
    if contratacion.estado == "formalizado":
        raise HTTPException(status_code=400, detail="No se pueden agregar documentos a una contratación formalizada")


def _subir_pdf_a_disco(id_contratacion: int, file: UploadFile) -> str:
    import uuid
    filename = f"{uuid.uuid4()}.pdf"
    MEDIA_DIR = Path(__file__).parent.parent / "media" / f"contratos/{id_contratacion}"
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = MEDIA_DIR / filename
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"/media/contratos/{id_contratacion}/{filename}"


def _crear_o_reemplazar_documento(
    db: Session,
    contratacion: ContratacionDocente,
    tipo: str,
    ruta_pdf: str | None,
    reemplazar_orden: int | None = None,
) -> DocumentoContratacion:
    if reemplazar_orden is not None:
        doc_existente = db.query(DocumentoContratacion).filter(
            DocumentoContratacion.id_contratacion == contratacion.id_contratacion,
            DocumentoContratacion.orden == reemplazar_orden,
        ).first()
        if not doc_existente:
            raise HTTPException(
                status_code=400,
                detail=f"No existe documento en la posición {reemplazar_orden}",
            )
        orden = reemplazar_orden
        disparar_gatillo = False
    else:
        doc_existente = None
        max_orden = db.query(DocumentoContratacion.orden).filter(
            DocumentoContratacion.id_contratacion == contratacion.id_contratacion
        ).order_by(DocumentoContratacion.orden.desc()).first()
        orden = (max_orden[0] + 1) if max_orden else 0

        if orden >= MAX_DOCUMENTOS:
            raise HTTPException(
                status_code=400,
                detail="Ya se completaron todos los documentos de la ruta de contratación",
            )

        disparar_gatillo = orden in GATILLOS_POR_POSICION

    if not tipo:
        tipo = f"documento_{orden + 1}"

    nuevo = DocumentoContratacion(
        id_contratacion=contratacion.id_contratacion,
        tipo=tipo,
        archivo_pdf=ruta_pdf,
        orden=orden,
    )
    db.add(nuevo)
    db.flush()

    if not doc_existente and disparar_gatillo:
        contratacion.estado = GATILLOS_POR_POSICION[orden]

    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.post("/", response_model=DocumentoContratacionResponse, status_code=201)
def crear(data: DocumentoContratacionCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.crear"))):
    contratacion = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_contratacion == data.id_contratacion
    ).first()
    _validar_contratacion_activa(contratacion)

    ruta_pdf = None
    if data.archivo_pdf_base64:
        ruta_pdf = guardar_pdf_base64(
            data.archivo_pdf_base64,
            media_subdir=f"contratos/{data.id_contratacion}",
        )

    nuevo = _crear_o_reemplazar_documento(db, contratacion, data.tipo, ruta_pdf)
    return query_base(db).filter(
        DocumentoContratacion.id_documento == nuevo.id_documento
    ).first()


@router.post("/{id_contratacion}/subir-pdf", response_model=DocumentoContratacionResponse, status_code=201)
async def subir_pdf(
    id_contratacion: int,
    file: UploadFile = File(...),
    tipo: str = Form(""),
    orden: int | None = Form(None),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_permiso("contrataciones.editar")),
):
    contratacion = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_contratacion == id_contratacion
    ).first()
    _validar_contratacion_activa(contratacion)

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    if not tipo:
        tipo = Path(file.filename).stem

    ruta_pdf = _subir_pdf_a_disco(id_contratacion, file)
    nuevo = _crear_o_reemplazar_documento(db, contratacion, tipo, ruta_pdf, reemplazar_orden=orden)
    return query_base(db).filter(
        DocumentoContratacion.id_documento == nuevo.id_documento
    ).first()


@router.get("/", response_model=list[DocumentoContratacionResponse])
def listar(contratacion_id: int | None = None, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.ver"))):
    query = query_base(db)
    if contratacion_id:
        query = query.filter(DocumentoContratacion.id_contratacion == contratacion_id)
    query = query.order_by(DocumentoContratacion.orden.asc(), DocumentoContratacion.id_documento.asc())
    return query.all()


@router.get("/{id}", response_model=DocumentoContratacionResponse)
def obtener(id: int, db: Session = Depends(get_db), current_user: UserResponse = Depends(require_permiso("contrataciones.ver"))):
    doc = query_base(db).filter(
        DocumentoContratacion.id_documento == id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc
