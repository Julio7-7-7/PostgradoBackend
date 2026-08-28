from routers.auth import login, permisos
from routers.personas import alumnos as persona_alumnos
from routers.personas import docentes as persona_docentes
from routers.personas import usuarios, roles, persona
from routers.academicos import (
    programas, programa_version, programa_version_edicion,
    modulos, detalle_programa_modulo, horarios, modalidades,
    tipo_programa, tipo_descuento, requisitos, carreras,
)
from routers.inscripciones import (
    detalle_alumno, solicitudes, documentos,
    requisitos as solicitud_requisito,
    historial_modulo,
)
from routers.docentes import (
    contrataciones, etapas, documentos_control, documentos_contratacion,
)
from routers.notas import calificaciones, informes, certificados
from routers.pagos import matriz, transacciones, ordenes
from routers import dashboard

all_routers = [
    # Auth
    login.router,
    permisos.router,
    # Personas
    persona_alumnos.router,
    persona_docentes.router,
    usuarios.router,
    roles.router,
    persona.router,
    # Académicos
    tipo_programa.router,
    programas.router,
    programa_version.router,
    modulos.router,
    modalidades.router,
    carreras.router,
    programa_version_edicion.router,
    detalle_programa_modulo.router,
    horarios.router,
    tipo_descuento.router,
    requisitos.router,
    # Inscripciones
    detalle_alumno.router,
    documentos.router,
    solicitud_requisito.router,
    historial_modulo.router,
    solicitudes.router,
    # Docentes
    contrataciones.router,
    documentos_contratacion.router,
    etapas.router,
    documentos_control.router,
    # Notas
    calificaciones.router,
    informes.router,
    certificados.router,
    # Pagos
    matriz.router,
    transacciones.router,
    ordenes.router,
    # Dashboard
    dashboard.router,
]
