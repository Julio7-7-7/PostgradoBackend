from database import SessionLocal
from models import Rol, Permiso, RolesPermiso, ModalidadAcademica, Requisito, Usuario, UsuarioRol, Alumno, Docente, Administrativo, TipoPrograma, ModalidadRequisito
from models.tipo_descuento import TipoDescuento
from models.modalidad_tipo_descuento import ModalidadTipoDescuento
from models.tipo_descuento_requisito import TipoDescuentoRequisito
from models.modalidad_tipo_programa import ModalidadTipoPrograma
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
        "modalidades_academicas.ver", "modalidades_academicas.crear", "modalidades_academicas.editar",
        "requisitos.ver", "requisitos.crear", "requisitos.editar", "requisitos.eliminar",
        "tipos_descuento.ver", "tipos_descuento.crear", "tipos_descuento.editar", "tipos_descuento.eliminar",

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
            "modalidades_academicas.ver", "modalidades_academicas.crear", "modalidades_academicas.editar",
            "requisitos.ver", "requisitos.crear", "requisitos.editar", "requisitos.eliminar",
            "tipos_descuento.ver", "tipos_descuento.crear", "tipos_descuento.editar", "tipos_descuento.eliminar",
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
            "docentes.ver",
        ],

        "alumno": [
            "dashboard.ver",
            "notas.ver",
            "alumnos.ver",
            "ediciones.ver",
            "modalidades_academicas.ver",
            "tipos_descuento.ver",
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

    modalidad_ed_continua = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.nombre_modalidad == "Educación Continua"
    ).first()
    if not modalidad_ed_continua:
        modalidad_ed_continua = ModalidadAcademica(
            nombre_modalidad="Educación Continua",
            descripcion="Modalidad de educación continua para programas de actualización y especialización",
            estado="activo",
        )
        db.add(modalidad_ed_continua)
        db.commit()
        db.refresh(modalidad_ed_continua)
        print(f"  ✅ Modalidad: {modalidad_ed_continua.nombre_modalidad}")
    else:
        print(f"  🔄 Modalidad: {modalidad_ed_continua.nombre_modalidad}")

    requisitos_data = [
        {"nombre": "Fotocopia de Carnet", "descripcion": "Fotocopia simple del carnet de identidad vigente"},
        {"nombre": "Boleta de GRL", "descripcion": "Boleta de pago del Gobierno Regional de La Paz"},
        {"nombre": "Avance Académico de la UAGRM", "descripcion": "Avance académico emitido por la Universidad Autónoma Gabriel René Moreno"},
    ]
    requisitos_objs = {}
    for req in requisitos_data:
        existente = db.query(Requisito).filter(Requisito.nombre == req["nombre"]).first()
        if not existente:
            req_obj = Requisito(
                nombre=req["nombre"],
                descripcion=req["descripcion"],
                estado="activo",
            )
            db.add(req_obj)
            db.commit()
            db.refresh(req_obj)
            requisitos_objs[req["nombre"]] = req_obj
            print(f"    ✅ Requisito: {req['nombre']}")
        else:
            requisitos_objs[req["nombre"]] = existente
            print(f"    🔄 Requisito: {existente.nombre}")

    vinculos_ed_continua = [
        "Fotocopia de Carnet", "Boleta de GRL", "Avance Académico de la UAGRM"
    ]
    for nombre_req in vinculos_ed_continua:
        req_obj = requisitos_objs[nombre_req]
        vinculo = db.query(ModalidadRequisito).filter(
            ModalidadRequisito.id_modalidad_academica == modalidad_ed_continua.id_modalidad_academica,
            ModalidadRequisito.id_requisito == req_obj.id_requisito,
        ).first()
        if not vinculo:
            db.add(ModalidadRequisito(
                id_modalidad_academica=modalidad_ed_continua.id_modalidad_academica,
                id_requisito=req_obj.id_requisito,
            ))
            db.commit()
            print(f"    ✅ {nombre_req} → Educación Continua")
        else:
            print(f"    🔄 {nombre_req} → Educación Continua ya vinculado")

    modalidad_profesionales = db.query(ModalidadAcademica).filter(
        ModalidadAcademica.nombre_modalidad == "Profesionales"
    ).first()
    if not modalidad_profesionales:
        modalidad_profesionales = ModalidadAcademica(
            nombre_modalidad="Profesionales",
            descripcion="Modalidad de formación profesional con título oficial",
            requiere_titulo=True,
            estado="activo",
        )
        db.add(modalidad_profesionales)
        db.commit()
        db.refresh(modalidad_profesionales)
        print(f"  ✅ Modalidad: {modalidad_profesionales.nombre_modalidad}")
    else:
        print(f"  🔄 Modalidad: {modalidad_profesionales.nombre_modalidad}")

    requisitos_prof = ["Avance Académico de la UAGRM"]
    for nombre_req in requisitos_prof:
        req_obj = requisitos_objs[nombre_req]
        vinculo = db.query(ModalidadRequisito).filter(
            ModalidadRequisito.id_modalidad_academica == modalidad_profesionales.id_modalidad_academica,
            ModalidadRequisito.id_requisito == req_obj.id_requisito,
        ).first()
        if not vinculo:
            db.add(ModalidadRequisito(
                id_modalidad_academica=modalidad_profesionales.id_modalidad_academica,
                id_requisito=req_obj.id_requisito,
            ))
            db.commit()
            print(f"    ✅ {nombre_req} → Profesionales")
        else:
            print(f"    🔄 {nombre_req} → Profesionales ya vinculado")

    requisito_beca = db.query(Requisito).filter(
        Requisito.nombre == "Media Beca UAGRM"
    ).first()
    if not requisito_beca:
        requisito_beca = Requisito(
            nombre="Media Beca UAGRM",
            descripcion="Documento que acredita media beca de la Universidad Autónoma Gabriel René Moreno",
            estado="activo",
        )
        db.add(requisito_beca)
        db.commit()
        db.refresh(requisito_beca)
        print(f"  ✅ Requisito (descuento): Media Beca UAGRM")
    else:
        print(f"  🔄 Requisito (descuento): Media Beca UAGRM")

    tipos_programa_data = [
        {"nombre": "Diplomado", "duracion_minima_meses": 6},
        {"nombre": "Maestría", "duracion_minima_meses": 18},
        {"nombre": "Curso", "duracion_minima_meses": 3},
    ]
    tipos_programa = {}
    for tp_data in tipos_programa_data:
        tp = db.query(TipoPrograma).filter(TipoPrograma.nombre == tp_data["nombre"]).first()
        if not tp:
            tp = TipoPrograma(nombre=tp_data["nombre"], duracion_minima_meses=tp_data["duracion_minima_meses"], estado="activo")
            db.add(tp)
            db.commit()
            db.refresh(tp)
            print(f"  ✅ Tipo de programa: {tp.nombre}")
        else:
            print(f"  🔄 Tipo de programa: {tp.nombre}")
        tipos_programa[tp.nombre] = tp

    modalidades_programa = {
        "Diplomado": [modalidad_ed_continua, modalidad_profesionales],
        "Maestría": [modalidad_profesionales],
        "Curso": [modalidad_profesionales],
    }
    for nombre_tp, mods in modalidades_programa.items():
        tp = tipos_programa[nombre_tp]
        for mod in mods:
            vinculo = db.query(ModalidadTipoPrograma).filter(
                ModalidadTipoPrograma.id_tipo_programa == tp.id_tipo_programa,
                ModalidadTipoPrograma.id_modalidad_academica == mod.id_modalidad_academica,
            ).first()
            if not vinculo:
                db.add(ModalidadTipoPrograma(
                    id_tipo_programa=tp.id_tipo_programa,
                    id_modalidad_academica=mod.id_modalidad_academica,
                ))
                db.commit()
                print(f"  ✅ {nombre_tp} ↔ {mod.nombre_modalidad}")
            else:
                print(f"  🔄 {nombre_tp} ↔ {mod.nombre_modalidad} ya vinculado")

    descuento_beca = db.query(TipoDescuento).filter(
        TipoDescuento.nombre == "Beca 50%"
    ).first()
    if not descuento_beca:
        descuento_beca = TipoDescuento(
            nombre="Beca 50%",
            porcentaje=50.0,
            descripcion="Beca del 50% para estudiantes de Educación Continua. Uso único: el alumno puede reservarla para usarla cuando desee.",
            uso_unico=True,
            estado="activo",
        )
        db.add(descuento_beca)
        db.commit()
        db.refresh(descuento_beca)
        print(f"  ✅ Tipo descuento: Beca 50%")
    else:
        print(f"  🔄 Tipo descuento: Beca 50%")

    descuento_contado = db.query(TipoDescuento).filter(
        TipoDescuento.nombre == "Descuento 10% Pago al Contado"
    ).first()
    if not descuento_contado:
        descuento_contado = TipoDescuento(
            nombre="Descuento 10% Pago al Contado",
            porcentaje=10.0,
            descripcion="Descuento del 10% por pago al contado, aplica a todas las modalidades",
            estado="activo",
        )
        db.add(descuento_contado)
        db.commit()
        db.refresh(descuento_contado)
        print(f"  ✅ Tipo descuento: Descuento 10% Pago al Contado")
    else:
        print(f"  🔄 Tipo descuento: Descuento 10% Pago al Contado")

    vinculo = db.query(ModalidadTipoDescuento).filter(
        ModalidadTipoDescuento.id_modalidad_academica == modalidad_ed_continua.id_modalidad_academica,
        ModalidadTipoDescuento.id_tipo_descuento == descuento_beca.id_tipo_descuento,
    ).first()
    if not vinculo:
        db.add(ModalidadTipoDescuento(
            id_modalidad_academica=modalidad_ed_continua.id_modalidad_academica,
            id_tipo_descuento=descuento_beca.id_tipo_descuento,
        ))
        db.commit()
        print(f"  ✅ Beca 50% → Educación Continua")
    else:
        print(f"  🔄 Beca 50% → Educación Continua ya vinculado")

    vinculo2 = db.query(ModalidadTipoDescuento).filter(
        ModalidadTipoDescuento.id_modalidad_academica == modalidad_ed_continua.id_modalidad_academica,
        ModalidadTipoDescuento.id_tipo_descuento == descuento_contado.id_tipo_descuento,
    ).first()
    if not vinculo2:
        db.add(ModalidadTipoDescuento(
            id_modalidad_academica=modalidad_ed_continua.id_modalidad_academica,
            id_tipo_descuento=descuento_contado.id_tipo_descuento,
        ))
        db.commit()
        print(f"  ✅ Descuento 10% → Educación Continua")
    else:
        print(f"  🔄 Descuento 10% → Educación Continua ya vinculado")

    vinculo3 = db.query(ModalidadTipoDescuento).filter(
        ModalidadTipoDescuento.id_modalidad_academica == modalidad_profesionales.id_modalidad_academica,
        ModalidadTipoDescuento.id_tipo_descuento == descuento_contado.id_tipo_descuento,
    ).first()
    if not vinculo3:
        db.add(ModalidadTipoDescuento(
            id_modalidad_academica=modalidad_profesionales.id_modalidad_academica,
            id_tipo_descuento=descuento_contado.id_tipo_descuento,
        ))
        db.commit()
        print(f"  ✅ Descuento 10% → Profesionales")
    else:
        print(f"  🔄 Descuento 10% → Profesionales ya vinculado")

    vinculo_req = db.query(TipoDescuentoRequisito).filter(
        TipoDescuentoRequisito.id_tipo_descuento == descuento_beca.id_tipo_descuento,
        TipoDescuentoRequisito.id_requisito == requisito_beca.id_requisito,
    ).first()
    if not vinculo_req:
        db.add(TipoDescuentoRequisito(
            id_tipo_descuento=descuento_beca.id_tipo_descuento,
            id_requisito=requisito_beca.id_requisito,
        ))
        db.commit()
        print(f"  ✅ Beca 50% requiere: Media Beca UAGRM")
    else:
        print(f"  🔄 Beca 50% requiere: Media Beca UAGRM ya vinculado")

    email = "julio.toledo2030@gmail.com"
    password = pwd_context.hash("adminjt")

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        usuario = Usuario(email=email, password_hash=password, activo=True)
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        print(f"  ✅ Usuario: {email}")
    else:
        print(f"  🔄 Usuario ya existe: {email}")

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
                grado="Lic.",
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
        usuario_rol = db.query(UsuarioRol).filter(
            UsuarioRol.id_usuario == usuario.id_usuario,
            UsuarioRol.id_rol == rol.id_rol,
        ).first()
        if not usuario_rol:
            db.add(UsuarioRol(id_usuario=usuario.id_usuario, id_rol=rol.id_rol, rol_activo=(nombre_rol == "adm_informatico")))
            db.commit()
            print(f"  ✅ Rol asignado: {nombre_rol}")
        else:
            print(f"  🔄 Rol ya asignado: {nombre_rol}")

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
