from routers import tipo_programa
from routers import programa
from routers import programa_version
from routers import modulo
from routers import modalidad_academica
from routers import programa_version_edicion
from routers import docente
from routers import detalle_programa_modulo
from routers import horario
from routers import alumno
from routers import detalle_programa_alumno
from routers import requisito
from routers import control_documentacion
from routers import historial_modulo
from routers import tipo_descuento
from routers import contrataciones_docente
from routers import documentos_contratacion
from routers import auth
from routers import roles
from routers import permisos
from routers import usuarios
from routers import pago
from routers import nota
from routers import dashboard

all_routers = [
    tipo_programa.router,
    programa.router,
    programa_version.router,
    modulo.router,
    modalidad_academica.router,
    programa_version_edicion.router,
    docente.router,
    detalle_programa_modulo.router,
    horario.router,
    alumno.router,
    detalle_programa_alumno.router,
    requisito.router,
    control_documentacion.router,
    historial_modulo.router,
    tipo_descuento.router,
    contrataciones_docente.router,
    documentos_contratacion.router,
    auth.router,
    roles.router,
    permisos.router,
    usuarios.router,
    pago.router,
    nota.router,
    dashboard.router,
]