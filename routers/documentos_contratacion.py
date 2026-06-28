import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models.documento_contratacion import DocumentoContratacion
from models.contratacion_docente import ContratacionDocente
from schemas.documentos_contratacion import (
    DocumentoContratacionCreate,
    DocumentoContratacionUpdate,
    DocumentoContratacionResponse,
)
from routers.utils import guardar_pdf_base64

router = APIRouter(
    prefix="/documentos-contratacion",
    tags=["Documentos Contratacion"],
)

RUTA_DOCUMENTAL = [
    {"tipo": "invitacion",  "gatillo": "en_curso"},
    {"tipo": "aceptacion",  "gatillo": None},
    {"tipo": "solicitud",   "gatillo": None},
    {"tipo": "contrato",    "gatillo": "formalizado"},
]

TIPO_POSICION = {step["tipo"]: i for i, step in enumerate(RUTA_DOCUMENTAL)}


def query_base(db):
    return db.query(DocumentoContratacion).options(
        joinedload(DocumentoContratacion.contratacion),
    )


@router.post("/", response_model=DocumentoContratacionResponse, status_code=201)
def crear(data: DocumentoContratacionCreate, db: Session = Depends(get_db)):
    contratacion = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_contratacion == data.id_contratacion
    ).first()
    if not contratacion:
        raise HTTPException(status_code=400, detail="La contratación especificada no existe")
    if contratacion.estado == "truncado":
        raise HTTPException(status_code=400, detail="No se pueden agregar documentos a una contratación truncada")
    if contratacion.estado == "formalizado":
        raise HTTPException(status_code=400, detail="No se pueden agregar documentos a una contratación formalizada")

    max_orden = db.query(DocumentoContratacion.orden).filter(
        DocumentoContratacion.id_contratacion == data.id_contratacion
    ).order_by(DocumentoContratacion.orden.desc()).first()
    siguiente_orden = (max_orden[0] + 1) if max_orden else 0

    if siguiente_orden >= len(RUTA_DOCUMENTAL):
        raise HTTPException(
            status_code=400,
            detail="Ya se completaron todos los documentos de la ruta de contratación",
        )

    paso_esperado = RUTA_DOCUMENTAL[siguiente_orden]
    if data.tipo.value != paso_esperado["tipo"]:
        raise HTTPException(
            status_code=400,
            detail=f"El siguiente documento debe ser '{paso_esperado['tipo']}'",
        )

    ruta_pdf = None
    if data.archivo_pdf_base64:
        ruta_pdf = guardar_pdf_base64(
            data.archivo_pdf_base64,
            media_subdir=f"contratos/{data.id_contratacion}",
        )

    nuevo = DocumentoContratacion(
        id_contratacion=data.id_contratacion,
        tipo=data.tipo.value,
        archivo_pdf=ruta_pdf,
        orden=siguiente_orden,
    )
    db.add(nuevo)
    db.flush()

    if paso_esperado["gatillo"]:
        contratacion.estado = paso_esperado["gatillo"]

    db.commit()
    db.refresh(nuevo)
    return query_base(db).filter(
        DocumentoContratacion.id_documento == nuevo.id_documento
    ).first()


@router.post("/{id_contratacion}/subir-pdf", response_model=DocumentoContratacionResponse, status_code=201)
async def subir_pdf(
    id_contratacion: int,
    tipo: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contratacion = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_contratacion == id_contratacion
    ).first()
    if not contratacion:
        raise HTTPException(status_code=400, detail="La contratación especificada no existe")
    if contratacion.estado == "truncado":
        raise HTTPException(status_code=400, detail="No se pueden agregar documentos a una contratación truncada")
    if contratacion.estado == "formalizado":
        raise HTTPException(status_code=400, detail="No se pueden agregar documentos a una contratación formalizada")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    max_orden = db.query(DocumentoContratacion.orden).filter(
        DocumentoContratacion.id_contratacion == id_contratacion
    ).order_by(DocumentoContratacion.orden.desc()).first()
    siguiente_orden = (max_orden[0] + 1) if max_orden else 0

    if siguiente_orden >= len(RUTA_DOCUMENTAL):
        raise HTTPException(
            status_code=400,
            detail="Ya se completaron todos los documentos de la ruta de contratación",
        )

    paso_esperado = RUTA_DOCUMENTAL[siguiente_orden]
    if tipo != paso_esperado["tipo"]:
        raise HTTPException(
            status_code=400,
            detail=f"El siguiente documento debe ser '{paso_esperado['tipo']}'",
        )

    import uuid
    filename = f"{uuid.uuid4()}.pdf"
    MEDIA_DIR = Path(__file__).parent.parent / "media" / f"contratos/{id_contratacion}"
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = MEDIA_DIR / filename
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    ruta_pdf = f"/media/contratos/{id_contratacion}/{filename}"

    nuevo = DocumentoContratacion(
        id_contratacion=id_contratacion,
        tipo=tipo,
        archivo_pdf=ruta_pdf,
        orden=siguiente_orden,
    )
    db.add(nuevo)
    db.flush()

    if paso_esperado["gatillo"]:
        contratacion.estado = paso_esperado["gatillo"]

    db.commit()
    db.refresh(nuevo)
    return query_base(db).filter(
        DocumentoContratacion.id_documento == nuevo.id_documento
    ).first()


@router.get("/", response_model=list[DocumentoContratacionResponse])
def listar(contratacion_id: int | None = None, db: Session = Depends(get_db)):
    query = query_base(db)
    if contratacion_id:
        query = query.filter(DocumentoContratacion.id_contratacion == contratacion_id)
    query = query.order_by(DocumentoContratacion.orden.asc())
    return query.all()


@router.get("/{id}", response_model=DocumentoContratacionResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    doc = query_base(db).filter(
        DocumentoContratacion.id_documento == id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc


@router.patch("/{id}/cancelar", response_model=DocumentoContratacionResponse)
def cancelar(id: int, db: Session = Depends(get_db)):
    doc = query_base(db).filter(
        DocumentoContratacion.id_documento == id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    db.delete(doc)
    db.commit()
    return doc
