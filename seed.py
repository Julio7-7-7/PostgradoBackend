from database import SessionLocal
from models import Rol, Permiso, RolesPermiso, Usuario, Alumno, Docente, Administrativo
from passlib.context import CryptContext
from datetime import date

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()


def get_or_create(model, defaults=None, **kwargs):
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    instance = model(**kwargs, **(defaults or {}))
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance, True


def seed():
    roles_data = {
        "adm_informatico": "Acceso total al sistema. Gestiona roles, usuarios y configuración.",
        "adm_legal": "Gestiona programas, ediciones, módulos, docentes, contrataciones y revisión documental.",
        "adm_contable": "Registra y consulta pagos de estudiantes. Acceso limitado a alumnos.",
        "adm_director": "Aprueba informes finales, supervisa el sistema.",
        "adm_pasante": "Apoya en revisión de documentación y consulta de alumnos.",
        "docente": "Sube notas, consulta horarios y módulos asignados.",
        "alumno": "Consulta su perfil, documentación, pagos y notas.",
    }

    permisos = [
        "dashboard.ver",

        "programas.ver", "programas.crear", "programas.editar", "programas.eliminar",
        "ediciones.ver", "ediciones.crear", "ediciones.editar", "ediciones.eliminar",
        "modulos.ver", "modulos.crear", "modulos.editar", "modulos.eliminar",

        "docentes.ver", "docentes.crear", "docentes.editar", "docentes.eliminar",
        "contrataciones.ver", "contrataciones.crear", "contrataciones.editar",
        "horarios.ver", "horarios.crear", "horarios.editar",

        "alumnos.ver", "alumnos.crear", "alumnos.editar",
        "documentos.revisar", "documentos.aprobar",

        "pagos.ver", "pagos.registrar",

        "tipos_programa.ver", "tipos_programa.crear", "tipos_programa.editar",
        "modalidades_academicas.ver", "modalidades_academicas.editar",
        "requisitos.ver", "requisitos.crear", "requisitos.editar",
        "tipos_descuento.ver", "tipos_descuento.crear", "tipos_descuento.editar",

        "historial.ver",
        "notas.subir", "notas.ver", "notas.aprobar",

        "roles.gestionar",
        "usuarios.gestionar",
    ]

    roles_permisos_map = {
        "adm_informatico": permisos,

        "adm_legal": [
            "dashboard.ver",
            "programas.ver", "programas.crear", "programas.editar",
            "ediciones.ver", "ediciones.crear", "ediciones.editar",
            "modulos.ver", "modulos.crear", "modulos.editar",
            "docentes.ver", "docentes.crear", "docentes.editar",
            "contrataciones.ver", "contrataciones.crear", "contrataciones.editar",
            "horarios.ver", "horarios.crear", "horarios.editar",
            "alumnos.ver",
            "documentos.revisar", "documentos.aprobar",
            "tipos_programa.ver", "tipos_programa.crear", "tipos_programa.editar",
            "modalidades_academicas.ver", "modalidades_academicas.editar",
            "requisitos.ver", "requisitos.crear", "requisitos.editar",
            "tipos_descuento.ver", "tipos_descuento.crear", "tipos_descuento.editar",
            "historial.ver",
        ],

        "adm_contable": [
            "dashboard.ver",
            "alumnos.ver", "alumnos.editar",
            "pagos.ver", "pagos.registrar",
            "ediciones.ver",
            "tipos_descuento.ver", "tipos_descuento.editar",
            "historial.ver",
        ],

        "adm_director": [
            "dashboard.ver",
            "programas.ver", "programas.editar",
            "ediciones.ver",
            "modulos.ver",
            "docentes.ver",
            "contrataciones.ver",
            "alumnos.ver",
            "pagos.ver",
            "documentos.aprobar",
            "notas.ver", "notas.aprobar",
            "historial.ver",
            "modalidades_academicas.ver",
        ],

        "adm_pasante": [
            "dashboard.ver",
            "alumnos.ver",
            "documentos.revisar",
            "ediciones.ver",
            "programas.ver",
        ],

        "docente": [
            "dashboard.ver",
            "modulos.ver",
            "horarios.ver",
            "notas.subir", "notas.ver",
            "alumnos.ver",
        ],

        "alumno": [
            "dashboard.ver",
            "notas.ver",
        ],
    }

    for nombre, desc in roles_data.items():
        rol, created = get_or_create(Rol, nombre=nombre, descripcion=desc)
        print(f"  {'✅' if created else '🔄'} Rol: {nombre}")

    for codigo in permisos:
        perm, created = get_or_create(
            Permiso,
            codigo=codigo,
            descripcion=_descripcion_permiso(codigo),
        )
        if created:
            print(f"  {'✅' if created else '🔄'} Permiso: {codigo}")

    for nombre_rol, permisos_rol in roles_permisos_map.items():
        rol = db.query(Rol).filter(Rol.nombre == nombre_rol).first()
        for codigo in permisos_rol:
            perm = db.query(Permiso).filter(Permiso.codigo == codigo).first()
            if perm:
                exists = db.query(RolesPermiso).filter(
                    RolesPermiso.id_rol == rol.id_rol,
                    RolesPermiso.id_permiso == perm.id_permiso,
                ).first()
                if not exists:
                    db.add(RolesPermiso(id_rol=rol.id_rol, id_permiso=perm.id_permiso))
                    db.commit()
        print(f"  ✅ Permisos asignados a: {nombre_rol}")

    email = "julio.toledo2030@gmail.com"
    password = pwd_context.hash("123456")

    roles_usuario = {
        "adm_informatico": {
            "crear_perfil": lambda usr: get_or_create(
                Administrativo,
                ci="12345678",
                nombre="Julio",
                apellido="Toledo",
                cargo="Administrador Informático",
                correo=email,
                celular="70000000",
                id_usuario=usr.id_usuario,
            )
        },
        "docente": {
            "crear_perfil": lambda usr: get_or_create(
                Docente,
                ci="12345678",
                nombre="Julio",
                apellido="Toledo",
                genero="masculino",
                extension="LP",
                grado="Licenciado",
                titulo="Ingeniero de Sistemas",
                celular="70000000",
                correo=email,
                id_usuario=usr.id_usuario,
            )
        },
        "alumno": {
            "crear_perfil": lambda usr: get_or_create(
                Alumno,
                ci="12345678",
                nombre="Julio",
                apellido="Toledo",
                fecha_nacimiento=date(1995, 5, 15),
                genero="masculino",
                celular="70000000",
                correo=email,
                direccion="Calle Ficticia 123",
                id_usuario=usr.id_usuario,
            )
        },
    }

    for nombre_rol, cfg in roles_usuario.items():
        rol = db.query(Rol).filter(Rol.nombre == nombre_rol).first()
        usuario, created = get_or_create(
            Usuario,
            email=email,
            password_hash=password,
            id_rol=rol.id_rol,
            activo=True,
        )
        if created:
            print(f"  ✅ Usuario: {email} como {nombre_rol}")
        else:
            print(f"  🔄 Usuario ya existe: {email} como {nombre_rol}")

        cfg["crear_perfil"](usuario)
        print(f"  ✅ Perfil creado: {nombre_rol}")

    db.close()
    print("\nSeed completado.")


def _descripcion_permiso(codigo: str) -> str:
    descs = {
        "dashboard.ver": "Ver dashboard principal",
        "programas.ver": "Ver listado de programas",
        "programas.crear": "Crear nuevos programas",
        "programas.editar": "Editar programas existentes",
        "programas.eliminar": "Eliminar programas",
        "ediciones.ver": "Ver ediciones de programas",
        "ediciones.crear": "Crear nuevas ediciones",
        "ediciones.editar": "Editar ediciones existentes",
        "ediciones.eliminar": "Eliminar ediciones",
        "modulos.ver": "Ver módulos",
        "modulos.crear": "Crear módulos",
        "modulos.editar": "Editar módulos",
        "modulos.eliminar": "Eliminar módulos",
        "docentes.ver": "Ver listado de docentes",
        "docentes.crear": "Crear docentes",
        "docentes.editar": "Editar docentes",
        "docentes.eliminar": "Eliminar docentes",
        "contrataciones.ver": "Ver contrataciones",
        "contrataciones.crear": "Crear contrataciones",
        "contrataciones.editar": "Editar contrataciones",
        "horarios.ver": "Ver horarios",
        "horarios.crear": "Crear horarios",
        "horarios.editar": "Editar horarios",
        "alumnos.ver": "Ver listado de alumnos",
        "alumnos.crear": "Crear alumnos",
        "alumnos.editar": "Editar alumnos",
        "documentos.revisar": "Revisar documentos de alumnos",
        "documentos.aprobar": "Aprobar o rechazar documentos",
        "pagos.ver": "Ver registro de pagos",
        "pagos.registrar": "Registrar pagos",
        "tipos_programa.ver": "Ver tipos de programa",
        "tipos_programa.crear": "Crear tipos de programa",
        "tipos_programa.editar": "Editar tipos de programa",
        "modalidades_academicas.ver": "Ver modalidades académicas",
        "modalidades_academicas.editar": "Editar modalidades académicas",
        "requisitos.ver": "Ver requisitos",
        "requisitos.crear": "Crear requisitos",
        "requisitos.editar": "Editar requisitos",
        "tipos_descuento.ver": "Ver tipos de descuento",
        "tipos_descuento.crear": "Crear tipos de descuento",
        "tipos_descuento.editar": "Editar tipos de descuento",
        "historial.ver": "Ver historial de cambios",
        "notas.subir": "Subir notas de módulos",
        "notas.ver": "Ver notas",
        "notas.aprobar": "Aprobar informe final de notas",
        "roles.gestionar": "Gestionar roles y permisos",
        "usuarios.gestionar": "Gestionar usuarios del sistema",
    }
    return descs.get(codigo, "")


if __name__ == "__main__":
    print("Sembrando datos...")
    seed()
