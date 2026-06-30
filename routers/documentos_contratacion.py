import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models.documento_contratacion import DocumentoContratacion
from models.contratacion_docente import ContratacionDocente
from schemas.documentos_contratacion import (
    DocumentoContratacionCreate,
    DocumentoContratacionResponse,
)
from routers.utils import guardar_pdf_base64

router = APIRouter(
    prefix="/documentos-contratacion",
    tags=["Documentos Contratacion"],
)

RUTA_DOCUMENTAL = [
    # Etapa 1: Presupuesto
    {"tipo": "solicitud_verificacion_saldos",       "gatillo": "verificacion",  "etapa": "presupuesto"},
    {"tipo": "remision_saldo",                      "gatillo": None,            "etapa": "presupuesto"},
    {"tipo": "resolucion_dg_verificacion",          "gatillo": None,            "etapa": "presupuesto"},
    # Etapa 2: Convocatoria
    {"tipo": "terminos_referencia",                 "gatillo": "convocatoria",  "etapa": "convocatoria"},
    {"tipo": "solicitud_contratacion_consultor",    "gatillo": None,            "etapa": "convocatoria"},
    {"tipo": "acta_inicio_proceso",                 "gatillo": None,            "etapa": "convocatoria"},
    # Etapa 3: Selección
    {"tipo": "seleccion_docente",                   "gatillo": "seleccion",     "etapa": "seleccion"},
    {"tipo": "invitacion_dictar_modulo",            "gatillo": None,            "etapa": "seleccion"},
    {"tipo": "respuesta_invitacion",                "gatillo": None,            "etapa": "seleccion"},
    # Etapa 4: Resolución
    {"tipo": "resolucion_comite_academico",         "gatillo": "resolucion",    "etapa": "resolucion"},
    {"tipo": "resolucion_consejo_directivo",        "gatillo": None,            "etapa": "resolucion"},
    {"tipo": "resolucion_dg_designacion",           "gatillo": None,            "etapa": "resolucion"},
    # Etapa 5: Legal
    {"tipo": "solicitud_antecedentes",              "gatillo": "legal",         "etapa": "legal"},
    {"tipo": "formulario_antecedentes",             "gatillo": None,            "etapa": "legal"},
    {"tipo": "remision_proceso_contratacion",       "gatillo": None,            "etapa": "legal"},
    {"tipo": "formulario_notarial",                 "gatillo": None,            "etapa": "legal"},
    {"tipo": "informe_tecnico_recomendacion",       "gatillo": None,            "etapa": "legal"},
    {"tipo": "resolucion_administrativa",           "gatillo": None,            "etapa": "legal"},
    {"tipo": "informe_legal",                       "gatillo": None,            "etapa": "legal"},
    # Etapa 6: Contrato
    {"tipo": "contrato",                            "gatillo": "formalizado",   "etapa": "contrato"},
]

TIPO_POSICION = {step["tipo"]: i for i, step in enumerate(RUTA_DOCUMENTAL)}


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
) -> DocumentoContratacion:
    tipo_orden = TIPO_POSICION.get(tipo)
    if tipo_orden is None:
        raise HTTPException(status_code=400, detail=f"Tipo de documento '{tipo}' no válido")

    doc_existente = db.query(DocumentoContratacion).filter(
        DocumentoContratacion.id_contratacion == contratacion.id_contratacion,
        DocumentoContratacion.tipo == tipo,
    ).first()

    if doc_existente:
        orden = doc_existente.orden
        disparar_gatillo = False
    else:
        max_orden = db.query(DocumentoContratacion.orden).filter(
            DocumentoContratacion.id_contratacion == contratacion.id_contratacion
        ).order_by(DocumentoContratacion.orden.desc()).first()
        orden = (max_orden[0] + 1) if max_orden else 0

        if orden >= len(RUTA_DOCUMENTAL):
            raise HTTPException(
                status_code=400,
                detail="Ya se completaron todos los documentos de la ruta de contratación",
            )

        paso_esperado = RUTA_DOCUMENTAL[orden]
        if tipo != paso_esperado["tipo"]:
            raise HTTPException(
                status_code=400,
                detail=f"El siguiente documento debe ser '{paso_esperado['tipo']}'",
            )

        disparar_gatillo = paso_esperado["gatillo"] is not None

    nuevo = DocumentoContratacion(
        id_contratacion=contratacion.id_contratacion,
        tipo=tipo,
        archivo_pdf=ruta_pdf,
        orden=orden,
    )
    db.add(nuevo)
    db.flush()

    if not doc_existente and disparar_gatillo:
        contratacion.estado = paso_esperado["gatillo"]

    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.post("/", response_model=DocumentoContratacionResponse, status_code=201)
def crear(data: DocumentoContratacionCreate, db: Session = Depends(get_db)):
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
    tipo: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contratacion = db.query(ContratacionDocente).filter(
        ContratacionDocente.id_contratacion == id_contratacion
    ).first()
    _validar_contratacion_activa(contratacion)

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    ruta_pdf = _subir_pdf_a_disco(id_contratacion, file)
    nuevo = _crear_o_reemplazar_documento(db, contratacion, tipo, ruta_pdf)
    return query_base(db).filter(
        DocumentoContratacion.id_documento == nuevo.id_documento
    ).first()


@router.get("/", response_model=list[DocumentoContratacionResponse])
def listar(contratacion_id: int | None = None, db: Session = Depends(get_db)):
    query = query_base(db)
    if contratacion_id:
        query = query.filter(DocumentoContratacion.id_contratacion == contratacion_id)
    query = query.order_by(DocumentoContratacion.orden.asc(), DocumentoContratacion.id_documento.asc())
    return query.all()


@router.get("/{id}", response_model=DocumentoContratacionResponse)
def obtener(id: int, db: Session = Depends(get_db)):
    doc = query_base(db).filter(
        DocumentoContratacion.id_documento == id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc
