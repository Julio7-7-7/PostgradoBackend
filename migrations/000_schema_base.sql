-- ============================================================
-- Migración 000: Schema base consolidado
-- Fecha: 2026-08-24
-- Descripción: Dump del esquema completo de la BD local.
--              Reemplaza las migraciones 003–020 individuales.
--              Las migraciones originales se conservan en
--              migrations/backup/ como referencia histórica.
-- ============================================================

-- PostgreSQL database dump
-- Name: administrativos; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.administrativos (
    id_administrativo integer NOT NULL,
    ci character varying(20) NOT NULL,
    nombre character varying(100) NOT NULL,
    apellido character varying(100) NOT NULL,
    cargo character varying(50),
    correo character varying(100),
    celular character varying(20),
    id_usuario integer,
    estado character varying(20) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: administrativos_id_administrativo_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.administrativos_id_administrativo_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: administrativos_id_administrativo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.administrativos_id_administrativo_seq OWNED BY public.administrativos.id_administrativo;
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);
-- Name: alumnos; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.alumnos (
    id_alumno integer CONSTRAINT alumno_id_alumno_not_null NOT NULL,
    ci character varying(20),
    nombre character varying(100) CONSTRAINT alumno_nombre_not_null NOT NULL,
    apellido character varying(100) CONSTRAINT alumno_apellido_not_null NOT NULL,
    fecha_nacimiento date,
    genero character varying,
    celular character varying(20),
    correo character varying(100) CONSTRAINT alumno_correo_not_null NOT NULL,
    direccion character varying(300),
    created_at timestamp without time zone DEFAULT now() CONSTRAINT alumno_created_at_not_null NOT NULL,
    updated_at timestamp without time zone DEFAULT now() CONSTRAINT alumno_updated_at_not_null NOT NULL,
    pasaporte character varying(30),
    id_usuario integer
);
-- Name: alumno_id_alumno_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.alumno_id_alumno_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: alumno_id_alumno_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.alumno_id_alumno_seq OWNED BY public.alumnos.id_alumno;
-- Name: certificados_notas; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.certificados_notas (
    id_certificado integer NOT NULL,
    id_alumno integer NOT NULL,
    id_programa_version_edicion integer NOT NULL,
    id_informe integer NOT NULL,
    fecha_emision date DEFAULT CURRENT_DATE NOT NULL,
    ruta_pdf text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);
-- Name: certificados_notas_id_certificado_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.certificados_notas_id_certificado_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: certificados_notas_id_certificado_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.certificados_notas_id_certificado_seq OWNED BY public.certificados_notas.id_certificado;
-- Name: contratacion_docente; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.contratacion_docente (
    id_contratacion integer NOT NULL,
    id_docente integer NOT NULL,
    id_detalle_modulo integer NOT NULL,
    monto numeric(10,2),
    estado character varying(30) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    fecha_inicio date,
    fecha_fin date,
    id_etapa_actual integer
);
-- Name: contratacion_docente_id_contratacion_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.contratacion_docente_id_contratacion_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: contratacion_docente_id_contratacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.contratacion_docente_id_contratacion_seq OWNED BY public.contratacion_docente.id_contratacion;
-- Name: control_documentacion; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.control_documentacion (
    id_control_documentacion integer NOT NULL,
    id_detalle_programa_alumno integer NOT NULL,
    id_requisito integer NOT NULL,
    fecha_entrega date,
    observaciones character varying,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    url_documento character varying(500),
    estado character varying(20) DEFAULT 'pendiente'::character varying NOT NULL,
    fecha_revision date,
    obligatorio boolean DEFAULT false NOT NULL
);
-- Name: control_documentacion_contratacion; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.control_documentacion_contratacion (
    id_control_doc_contratacion integer CONSTRAINT control_documentacion_contr_id_control_doc_contratacio_not_null NOT NULL,
    id_contratacion integer NOT NULL,
    id_requisito integer NOT NULL,
    id_etapa integer NOT NULL,
    url_documento character varying(500),
    estado character varying(20) DEFAULT 'pendiente'::character varying NOT NULL,
    notas character varying(500),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: control_documentacion_contratac_id_control_doc_contratacion_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.control_documentacion_contratac_id_control_doc_contratacion_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: control_documentacion_contratac_id_control_doc_contratacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.control_documentacion_contratac_id_control_doc_contratacion_seq OWNED BY public.control_documentacion_contratacion.id_control_doc_contratacion;
-- Name: control_documentacion_id_control_documentacion_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.control_documentacion_id_control_documentacion_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: control_documentacion_id_control_documentacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.control_documentacion_id_control_documentacion_seq OWNED BY public.control_documentacion.id_control_documentacion;
-- Name: detalle_programa_alumno; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.detalle_programa_alumno (
    id_detalle_programa_alumno integer NOT NULL,
    id_programa_version_edicion integer NOT NULL,
    id_alumno integer NOT NULL,
    id_modalidad_academica integer NOT NULL,
    estado character varying NOT NULL,
    fecha_inscripcion date,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    id_tipo_descuento integer,
    descuento_aplicado numeric(5,2) DEFAULT '0'::double precision NOT NULL,
    modulo_inicio integer DEFAULT 1 NOT NULL,
    es_incorporacion boolean DEFAULT false NOT NULL,
    id_modulo_inicio integer
);
-- Name: detalle_programa_alumno_id_detalle_programa_alumno_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.detalle_programa_alumno_id_detalle_programa_alumno_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: detalle_programa_alumno_id_detalle_programa_alumno_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.detalle_programa_alumno_id_detalle_programa_alumno_seq OWNED BY public.detalle_programa_alumno.id_detalle_programa_alumno;
-- Name: detalle_programa_modulo; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.detalle_programa_modulo (
    id_detalle_programa_modulo integer NOT NULL,
    id_programa_version_edicion integer NOT NULL,
    id_modulo integer NOT NULL,
    fecha_inicio date,
    fecha_fin date,
    estado character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    orden integer NOT NULL,
    modalidad character varying(50)
);
-- Name: detalle_programa_modulo_id_detalle_programa_modulo_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.detalle_programa_modulo_id_detalle_programa_modulo_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: detalle_programa_modulo_id_detalle_programa_modulo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.detalle_programa_modulo_id_detalle_programa_modulo_seq OWNED BY public.detalle_programa_modulo.id_detalle_programa_modulo;
-- Name: docentes; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.docentes (
    id_docente integer CONSTRAINT docente_id_docente_not_null NOT NULL,
    ci character varying(20) CONSTRAINT docente_ci_not_null NOT NULL,
    nombre character varying(100) CONSTRAINT docente_nombre_not_null NOT NULL,
    apellido character varying(100) CONSTRAINT docente_apellido_not_null NOT NULL,
    celular character varying(20),
    correo character varying(100) CONSTRAINT docente_correo_not_null NOT NULL,
    created_at timestamp without time zone DEFAULT now() CONSTRAINT docente_created_at_not_null NOT NULL,
    updated_at timestamp without time zone DEFAULT now() CONSTRAINT docente_updated_at_not_null NOT NULL,
    genero character varying(20),
    titulo character varying(100),
    estado character varying(20) DEFAULT 'disponible'::character varying NOT NULL,
    grado character varying(50),
    extension character varying(5),
    id_usuario integer
);
-- Name: docente_id_docente_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.docente_id_docente_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: docente_id_docente_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.docente_id_docente_seq OWNED BY public.docentes.id_docente;
-- Name: documento_solicitud; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.documento_solicitud (
    id_solicitud_documento integer CONSTRAINT solicitud_documento_id_solicitud_documento_not_null NOT NULL,
    id_solicitud integer CONSTRAINT solicitud_documento_id_solicitud_not_null NOT NULL,
    id_requisito integer CONSTRAINT solicitud_documento_id_requisito_not_null NOT NULL,
    url_documento character varying(500) CONSTRAINT solicitud_documento_url_documento_not_null NOT NULL,
    estado character varying(20) DEFAULT 'pendiente'::character varying CONSTRAINT solicitud_documento_estado_not_null NOT NULL,
    fecha_entrega timestamp without time zone
);
-- Name: documento_solicitud_id_documento_solicitud_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.documento_solicitud_id_documento_solicitud_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: documento_solicitud_id_documento_solicitud_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.documento_solicitud_id_documento_solicitud_seq OWNED BY public.documento_solicitud.id_solicitud_documento;
-- Name: documentos_contratacion; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.documentos_contratacion (
    id_documento integer NOT NULL,
    id_contratacion integer NOT NULL,
    tipo character varying(80) NOT NULL,
    archivo_pdf character varying(500),
    fecha_subida timestamp without time zone DEFAULT now() NOT NULL,
    orden integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: documentos_contratacion_id_documento_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.documentos_contratacion_id_documento_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: documentos_contratacion_id_documento_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.documentos_contratacion_id_documento_seq OWNED BY public.documentos_contratacion.id_documento;
-- Name: etapa_contratacion; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.etapa_contratacion (
    id_etapa integer NOT NULL,
    id_tipo_programa integer NOT NULL,
    nombre character varying(200) NOT NULL,
    orden integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: etapa_contratacion_id_etapa_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.etapa_contratacion_id_etapa_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: etapa_contratacion_id_etapa_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.etapa_contratacion_id_etapa_seq OWNED BY public.etapa_contratacion.id_etapa;
-- Name: etapa_requisito; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.etapa_requisito (
    id_etapa integer NOT NULL,
    id_requisito integer NOT NULL,
    orden integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: historial_inscripcion; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.historial_inscripcion (
    id_historial integer NOT NULL,
    id_detalle_origen integer NOT NULL,
    id_detalle_destino integer NOT NULL,
    motivo text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    tipo_movimiento character varying(20) DEFAULT 'transferencia'::character varying NOT NULL,
    id_solicitud integer
);
-- Name: historial_inscripcion_id_historial_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.historial_inscripcion_id_historial_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: historial_inscripcion_id_historial_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.historial_inscripcion_id_historial_seq OWNED BY public.historial_inscripcion.id_historial;
-- Name: historial_modulo; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.historial_modulo (
    id_historial integer NOT NULL,
    id_detalle_programa_modulo integer NOT NULL,
    estado_anterior character varying(20),
    estado_nuevo character varying(20),
    motivo character varying(500) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    fecha_inicio_original date,
    fecha_fin_original date,
    fecha_inicio_nuevo date,
    fecha_fin_nuevo date
);
-- Name: historial_modulo_id_historial_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.historial_modulo_id_historial_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: historial_modulo_id_historial_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.historial_modulo_id_historial_seq OWNED BY public.historial_modulo.id_historial;
-- Name: horarios; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.horarios (
    id_horario integer CONSTRAINT horario_id_horario_not_null NOT NULL,
    id_detalle_programa_modulo integer CONSTRAINT horario_id_detalle_programa_modulo_not_null NOT NULL,
    dia character varying(20) CONSTRAINT horario_dia_not_null NOT NULL,
    hora_ini time without time zone CONSTRAINT horario_hora_ini_not_null NOT NULL,
    hora_fin time without time zone CONSTRAINT horario_hora_fin_not_null NOT NULL,
    created_at timestamp without time zone DEFAULT now() CONSTRAINT horario_created_at_not_null NOT NULL,
    updated_at timestamp without time zone DEFAULT now() CONSTRAINT horario_updated_at_not_null NOT NULL,
    aula character varying(200),
    estado character varying(20) NOT NULL
);
-- Name: horario_id_horario_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.horario_id_horario_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: horario_id_horario_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.horario_id_horario_seq OWNED BY public.horarios.id_horario;
-- Name: informes_notas; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.informes_notas (
    id_informe integer NOT NULL,
    id_programa_version_edicion integer NOT NULL,
    numero_tanda integer NOT NULL,
    fecha_emision date DEFAULT CURRENT_DATE NOT NULL,
    alumnos_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    estado character varying(20) DEFAULT 'borrador'::character varying NOT NULL,
    observaciones text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);
-- Name: informes_notas_id_informe_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.informes_notas_id_informe_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: informes_notas_id_informe_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.informes_notas_id_informe_seq OWNED BY public.informes_notas.id_informe;
-- Name: modalidades_academicas; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.modalidades_academicas (
    id_modalidad_academica integer CONSTRAINT modalidad_academica_id_modalidad_academica_not_null NOT NULL,
    nombre_modalidad character varying(100) CONSTRAINT modalidad_academica_nombre_modalidad_not_null NOT NULL,
    created_at timestamp without time zone DEFAULT now() CONSTRAINT modalidad_academica_created_at_not_null NOT NULL,
    updated_at timestamp without time zone DEFAULT now() CONSTRAINT modalidad_academica_updated_at_not_null NOT NULL,
    descripcion character varying(500),
    estado character varying(20) DEFAULT 'activo'::character varying NOT NULL
);
-- Name: modalidad_academica_id_modalidad_academica_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.modalidad_academica_id_modalidad_academica_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: modalidad_academica_id_modalidad_academica_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.modalidad_academica_id_modalidad_academica_seq OWNED BY public.modalidades_academicas.id_modalidad_academica;
-- Name: modalidad_requisito; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.modalidad_requisito (
    id_modalidad_academica integer NOT NULL,
    id_requisito integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: modalidad_tipo_descuento; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.modalidad_tipo_descuento (
    id_modalidad_academica integer NOT NULL,
    id_tipo_descuento integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: modalidad_tipo_programa; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.modalidad_tipo_programa (
    id_modalidad_academica integer NOT NULL,
    id_tipo_programa integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: modulos; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.modulos (
    id_modulo integer CONSTRAINT modulo_id_modulo_not_null NOT NULL,
    id_programa_version integer CONSTRAINT modulo_id_programa_version_not_null NOT NULL,
    sigla character varying(20) CONSTRAINT modulo_sigla_not_null NOT NULL,
    nombre_modulo character varying(200) CONSTRAINT modulo_nombre_modulo_not_null NOT NULL,
    horas_academicas integer CONSTRAINT modulo_horas_academicas_not_null NOT NULL,
    creditos integer CONSTRAINT modulo_creditos_not_null NOT NULL,
    descripcion character varying(500),
    created_at timestamp without time zone DEFAULT now() CONSTRAINT modulo_created_at_not_null NOT NULL,
    updated_at timestamp without time zone DEFAULT now() CONSTRAINT modulo_updated_at_not_null NOT NULL,
    estado character varying(20) DEFAULT 'activo'::character varying NOT NULL
);
-- Name: modulo_id_modulo_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.modulo_id_modulo_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: modulo_id_modulo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.modulo_id_modulo_seq OWNED BY public.modulos.id_modulo;
-- Name: notas; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.notas (
    id_nota integer NOT NULL,
    id_detalle_programa_alumno integer NOT NULL,
    id_detalle_programa_modulo integer NOT NULL,
    nota numeric(5,2) NOT NULL,
    fecha date NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: notas_id_nota_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.notas_id_nota_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: notas_id_nota_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.notas_id_nota_seq OWNED BY public.notas.id_nota;
-- Name: orden_pago; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.orden_pago (
    id_orden_pago integer NOT NULL,
    numero character varying(20) NOT NULL,
    id_detalle_programa_alumno integer NOT NULL,
    fecha_emision date DEFAULT CURRENT_DATE NOT NULL,
    monto_total numeric(10,2) NOT NULL,
    items jsonb DEFAULT '[]'::jsonb NOT NULL,
    estado character varying(20) DEFAULT 'emitida'::character varying NOT NULL,
    motivo_anulacion text,
    anulado_por_id_usuario integer,
    anulado_fecha timestamp without time zone,
    creado_por_id_usuario integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: orden_pago_id_orden_pago_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.orden_pago_id_orden_pago_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: orden_pago_id_orden_pago_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.orden_pago_id_orden_pago_seq OWNED BY public.orden_pago.id_orden_pago;
-- Name: pagos; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.pagos (
    id_pago integer NOT NULL,
    monto numeric(10,2) NOT NULL,
    concepto character varying(100) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    id_detalle_programa_modulo integer,
    id_transaccion integer NOT NULL
);
-- Name: pagos_id_pago_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.pagos_id_pago_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: pagos_id_pago_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.pagos_id_pago_seq OWNED BY public.pagos.id_pago;
-- Name: permisos; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.permisos (
    id_permiso integer NOT NULL,
    codigo character varying(100) NOT NULL,
    descripcion character varying(200),
    created_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: permisos_id_permiso_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.permisos_id_permiso_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: permisos_id_permiso_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.permisos_id_permiso_seq OWNED BY public.permisos.id_permiso;
-- Name: programas; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.programas (
    id_programa integer CONSTRAINT programa_id_programa_not_null NOT NULL,
    id_tipo_programa integer CONSTRAINT programa_id_tipo_programa_not_null NOT NULL,
    nombre_programa character varying(200) CONSTRAINT programa_nombre_programa_not_null NOT NULL,
    created_at timestamp without time zone DEFAULT now() CONSTRAINT programa_created_at_not_null NOT NULL,
    updated_at timestamp without time zone DEFAULT now() CONSTRAINT programa_updated_at_not_null NOT NULL,
    estado character varying(20) NOT NULL,
    foto character varying(500)
);
-- Name: programa_id_programa_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.programa_id_programa_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: programa_id_programa_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.programa_id_programa_seq OWNED BY public.programas.id_programa;
-- Name: programa_version_edicion; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.programa_version_edicion (
    id_programa_version_edicion integer NOT NULL,
    id_programa_version integer NOT NULL,
    edicion integer NOT NULL,
    fecha_inicio date,
    fecha_fin date,
    cupo_maximo integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    estado character varying(20) DEFAULT 'programado'::character varying NOT NULL,
    descripcion character varying(500),
    precio double precision,
    es_historico boolean NOT NULL,
    modalidad character varying(50) NOT NULL,
    semestre integer NOT NULL,
    anio integer NOT NULL,
    matricula double precision DEFAULT 0 NOT NULL
);
-- Name: programa_version_edicion_id_programa_version_edicion_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.programa_version_edicion_id_programa_version_edicion_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: programa_version_edicion_id_programa_version_edicion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.programa_version_edicion_id_programa_version_edicion_seq OWNED BY public.programa_version_edicion.id_programa_version_edicion;
-- Name: programas_version; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.programas_version (
    id_programa_version integer CONSTRAINT programa_version_id_programa_version_not_null NOT NULL,
    id_programa integer CONSTRAINT programa_version_id_programa_not_null NOT NULL,
    version integer CONSTRAINT programa_version_version_not_null NOT NULL,
    created_at timestamp without time zone DEFAULT now() CONSTRAINT programa_version_created_at_not_null NOT NULL,
    updated_at timestamp without time zone DEFAULT now() CONSTRAINT programa_version_updated_at_not_null NOT NULL,
    descripcion character varying(500),
    vigente boolean DEFAULT true NOT NULL,
    foto character varying(500)
);
-- Name: programa_version_id_programa_version_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.programa_version_id_programa_version_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: programa_version_id_programa_version_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.programa_version_id_programa_version_seq OWNED BY public.programas_version.id_programa_version;
-- Name: requisitos; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.requisitos (
    id_requisito integer CONSTRAINT requisito_id_requisito_not_null NOT NULL,
    nombre character varying(200) CONSTRAINT requisito_nombre_not_null NOT NULL,
    descripcion character varying(500),
    created_at timestamp without time zone DEFAULT now() CONSTRAINT requisito_created_at_not_null NOT NULL,
    updated_at timestamp without time zone DEFAULT now() CONSTRAINT requisito_updated_at_not_null NOT NULL,
    estado character varying(20) DEFAULT 'activo'::character varying NOT NULL,
    imagen_url character varying(500)
);
-- Name: requisito_id_requisito_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.requisito_id_requisito_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: requisito_id_requisito_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.requisito_id_requisito_seq OWNED BY public.requisitos.id_requisito;
-- Name: roles; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.roles (
    id_rol integer NOT NULL,
    nombre character varying(50) NOT NULL,
    descripcion character varying(200),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: roles_id_rol_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.roles_id_rol_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: roles_id_rol_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.roles_id_rol_seq OWNED BY public.roles.id_rol;
-- Name: roles_permisos; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.roles_permisos (
    id_rol integer NOT NULL,
    id_permiso integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: solicitud; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.solicitud (
    id_solicitud integer NOT NULL,
    id_tipo_solicitud integer NOT NULL,
    id_alumno integer NOT NULL,
    id_detalle_origen integer,
    estado character varying(20) DEFAULT 'pendiente'::character varying NOT NULL,
    motivo text,
    motivo_rechazo text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: solicitud_id_solicitud_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.solicitud_id_solicitud_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: solicitud_id_solicitud_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.solicitud_id_solicitud_seq OWNED BY public.solicitud.id_solicitud;
-- Name: solicitud_incorporacion; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.solicitud_incorporacion (
    id_solicitud integer NOT NULL,
    id_programa_version_edicion integer NOT NULL,
    id_modalidad_academica integer NOT NULL,
    id_tipo_descuento integer
);
-- Name: solicitud_migracion; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.solicitud_migracion (
    id_solicitud integer NOT NULL,
    id_edicion_destino integer NOT NULL,
    motivo text DEFAULT ''::text NOT NULL
);
-- Name: solicitud_requisito; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.solicitud_requisito (
    id_solicitud_requisito integer NOT NULL,
    id_requisito integer NOT NULL,
    estado character varying(20) DEFAULT 'activo'::character varying NOT NULL,
    id_tipo_solicitud integer NOT NULL
);
-- Name: solicitud_requisito_id_solicitud_requisito_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.solicitud_requisito_id_solicitud_requisito_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: solicitud_requisito_id_solicitud_requisito_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.solicitud_requisito_id_solicitud_requisito_seq OWNED BY public.solicitud_requisito.id_solicitud_requisito;
-- Name: tipo_descuento_requisito; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.tipo_descuento_requisito (
    id_tipo_descuento integer NOT NULL,
    id_requisito integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: tipos_programa; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.tipos_programa (
    id_tipo_programa integer CONSTRAINT tipo_programa_id_tipo_programa_not_null NOT NULL,
    nombre character varying(100) CONSTRAINT tipo_programa_nombre_not_null NOT NULL,
    created_at timestamp without time zone DEFAULT now() CONSTRAINT tipo_programa_created_at_not_null NOT NULL,
    updated_at timestamp without time zone DEFAULT now() CONSTRAINT tipo_programa_updated_at_not_null NOT NULL,
    estado character varying(20) DEFAULT 'activo'::character varying NOT NULL,
    cupo_minimo integer,
    duracion_minima_meses integer
);
-- Name: tipo_programa_id_tipo_programa_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.tipo_programa_id_tipo_programa_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: tipo_programa_id_tipo_programa_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.tipo_programa_id_tipo_programa_seq OWNED BY public.tipos_programa.id_tipo_programa;
-- Name: tipo_solicitud; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.tipo_solicitud (
    id_tipo_solicitud integer CONSTRAINT solicitud_tipo_id_solicitud_tipo_not_null NOT NULL,
    codigo character varying(30) CONSTRAINT solicitud_tipo_codigo_not_null NOT NULL,
    nombre character varying(100) CONSTRAINT solicitud_tipo_nombre_not_null NOT NULL
);
-- Name: tipo_solicitud_id_solicitud_tipo_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.tipo_solicitud_id_solicitud_tipo_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: tipo_solicitud_id_solicitud_tipo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.tipo_solicitud_id_solicitud_tipo_seq OWNED BY public.tipo_solicitud.id_tipo_solicitud;
-- Name: tipos_descuento; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.tipos_descuento (
    id_tipo_descuento integer NOT NULL,
    nombre character varying(100) NOT NULL,
    porcentaje double precision NOT NULL,
    descripcion character varying(500),
    estado character varying(20) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    uso_unico boolean DEFAULT false NOT NULL
);
-- Name: tipos_descuento_id_tipo_descuento_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.tipos_descuento_id_tipo_descuento_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: tipos_descuento_id_tipo_descuento_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.tipos_descuento_id_tipo_descuento_seq OWNED BY public.tipos_descuento.id_tipo_descuento;
-- Name: transaccion_pago; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.transaccion_pago (
    id_transaccion integer NOT NULL,
    id_detalle_programa_alumno integer NOT NULL,
    monto_total numeric(10,2) NOT NULL,
    fecha_pago date NOT NULL,
    comprobante character varying(500),
    estado character varying(20) DEFAULT 'confirmado'::character varying NOT NULL,
    motivo_anulacion text,
    anulado_por_id_usuario integer,
    anulado_fecha timestamp without time zone,
    creado_por_id_usuario integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    id_orden_pago integer
);
-- Name: transaccion_pago_id_transaccion_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.transaccion_pago_id_transaccion_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: transaccion_pago_id_transaccion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.transaccion_pago_id_transaccion_seq OWNED BY public.transaccion_pago.id_transaccion;
-- Name: usuario_roles; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.usuario_roles (
    id_usuario integer NOT NULL,
    id_rol integer NOT NULL,
    rol_activo boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);
-- Name: usuarios; Type: TABLE; Schema: public; Owner: -
CREATE TABLE public.usuarios (
    id_usuario integer NOT NULL,
    email character varying(100) NOT NULL,
    password_hash character varying(200) NOT NULL,
    activo boolean NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    must_change_password boolean DEFAULT false NOT NULL,
    password_changed_at timestamp without time zone DEFAULT now() NOT NULL
);
-- Name: usuarios_id_usuario_seq; Type: SEQUENCE; Schema: public; Owner: -
CREATE SEQUENCE public.usuarios_id_usuario_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
-- Name: usuarios_id_usuario_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
ALTER SEQUENCE public.usuarios_id_usuario_seq OWNED BY public.usuarios.id_usuario;
-- Name: administrativos id_administrativo; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.administrativos ALTER COLUMN id_administrativo SET DEFAULT nextval('public.administrativos_id_administrativo_seq'::regclass);
-- Name: alumnos id_alumno; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.alumnos ALTER COLUMN id_alumno SET DEFAULT nextval('public.alumno_id_alumno_seq'::regclass);
-- Name: certificados_notas id_certificado; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.certificados_notas ALTER COLUMN id_certificado SET DEFAULT nextval('public.certificados_notas_id_certificado_seq'::regclass);
-- Name: contratacion_docente id_contratacion; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.contratacion_docente ALTER COLUMN id_contratacion SET DEFAULT nextval('public.contratacion_docente_id_contratacion_seq'::regclass);
-- Name: control_documentacion id_control_documentacion; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.control_documentacion ALTER COLUMN id_control_documentacion SET DEFAULT nextval('public.control_documentacion_id_control_documentacion_seq'::regclass);
-- Name: control_documentacion_contratacion id_control_doc_contratacion; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.control_documentacion_contratacion ALTER COLUMN id_control_doc_contratacion SET DEFAULT nextval('public.control_documentacion_contratac_id_control_doc_contratacion_seq'::regclass);
-- Name: detalle_programa_alumno id_detalle_programa_alumno; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.detalle_programa_alumno ALTER COLUMN id_detalle_programa_alumno SET DEFAULT nextval('public.detalle_programa_alumno_id_detalle_programa_alumno_seq'::regclass);
-- Name: detalle_programa_modulo id_detalle_programa_modulo; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.detalle_programa_modulo ALTER COLUMN id_detalle_programa_modulo SET DEFAULT nextval('public.detalle_programa_modulo_id_detalle_programa_modulo_seq'::regclass);
-- Name: docentes id_docente; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.docentes ALTER COLUMN id_docente SET DEFAULT nextval('public.docente_id_docente_seq'::regclass);
-- Name: documento_solicitud id_solicitud_documento; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.documento_solicitud ALTER COLUMN id_solicitud_documento SET DEFAULT nextval('public.documento_solicitud_id_documento_solicitud_seq'::regclass);
-- Name: documentos_contratacion id_documento; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.documentos_contratacion ALTER COLUMN id_documento SET DEFAULT nextval('public.documentos_contratacion_id_documento_seq'::regclass);
-- Name: etapa_contratacion id_etapa; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.etapa_contratacion ALTER COLUMN id_etapa SET DEFAULT nextval('public.etapa_contratacion_id_etapa_seq'::regclass);
-- Name: historial_inscripcion id_historial; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.historial_inscripcion ALTER COLUMN id_historial SET DEFAULT nextval('public.historial_inscripcion_id_historial_seq'::regclass);
-- Name: historial_modulo id_historial; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.historial_modulo ALTER COLUMN id_historial SET DEFAULT nextval('public.historial_modulo_id_historial_seq'::regclass);
-- Name: horarios id_horario; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.horarios ALTER COLUMN id_horario SET DEFAULT nextval('public.horario_id_horario_seq'::regclass);
-- Name: informes_notas id_informe; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.informes_notas ALTER COLUMN id_informe SET DEFAULT nextval('public.informes_notas_id_informe_seq'::regclass);
-- Name: modalidades_academicas id_modalidad_academica; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.modalidades_academicas ALTER COLUMN id_modalidad_academica SET DEFAULT nextval('public.modalidad_academica_id_modalidad_academica_seq'::regclass);
-- Name: modulos id_modulo; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.modulos ALTER COLUMN id_modulo SET DEFAULT nextval('public.modulo_id_modulo_seq'::regclass);
-- Name: notas id_nota; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.notas ALTER COLUMN id_nota SET DEFAULT nextval('public.notas_id_nota_seq'::regclass);
-- Name: orden_pago id_orden_pago; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.orden_pago ALTER COLUMN id_orden_pago SET DEFAULT nextval('public.orden_pago_id_orden_pago_seq'::regclass);
-- Name: pagos id_pago; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.pagos ALTER COLUMN id_pago SET DEFAULT nextval('public.pagos_id_pago_seq'::regclass);
-- Name: permisos id_permiso; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.permisos ALTER COLUMN id_permiso SET DEFAULT nextval('public.permisos_id_permiso_seq'::regclass);
-- Name: programa_version_edicion id_programa_version_edicion; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.programa_version_edicion ALTER COLUMN id_programa_version_edicion SET DEFAULT nextval('public.programa_version_edicion_id_programa_version_edicion_seq'::regclass);
-- Name: programas id_programa; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.programas ALTER COLUMN id_programa SET DEFAULT nextval('public.programa_id_programa_seq'::regclass);
-- Name: programas_version id_programa_version; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.programas_version ALTER COLUMN id_programa_version SET DEFAULT nextval('public.programa_version_id_programa_version_seq'::regclass);
-- Name: requisitos id_requisito; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.requisitos ALTER COLUMN id_requisito SET DEFAULT nextval('public.requisito_id_requisito_seq'::regclass);
-- Name: roles id_rol; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.roles ALTER COLUMN id_rol SET DEFAULT nextval('public.roles_id_rol_seq'::regclass);
-- Name: solicitud id_solicitud; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud ALTER COLUMN id_solicitud SET DEFAULT nextval('public.solicitud_id_solicitud_seq'::regclass);
-- Name: solicitud_requisito id_solicitud_requisito; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud_requisito ALTER COLUMN id_solicitud_requisito SET DEFAULT nextval('public.solicitud_requisito_id_solicitud_requisito_seq'::regclass);
-- Name: tipo_solicitud id_tipo_solicitud; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.tipo_solicitud ALTER COLUMN id_tipo_solicitud SET DEFAULT nextval('public.tipo_solicitud_id_solicitud_tipo_seq'::regclass);
-- Name: tipos_descuento id_tipo_descuento; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.tipos_descuento ALTER COLUMN id_tipo_descuento SET DEFAULT nextval('public.tipos_descuento_id_tipo_descuento_seq'::regclass);
-- Name: tipos_programa id_tipo_programa; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.tipos_programa ALTER COLUMN id_tipo_programa SET DEFAULT nextval('public.tipo_programa_id_tipo_programa_seq'::regclass);
-- Name: transaccion_pago id_transaccion; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.transaccion_pago ALTER COLUMN id_transaccion SET DEFAULT nextval('public.transaccion_pago_id_transaccion_seq'::regclass);
-- Name: usuarios id_usuario; Type: DEFAULT; Schema: public; Owner: -
ALTER TABLE ONLY public.usuarios ALTER COLUMN id_usuario SET DEFAULT nextval('public.usuarios_id_usuario_seq'::regclass);
-- Name: administrativos administrativos_ci_key; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.administrativos
    ADD CONSTRAINT administrativos_ci_key UNIQUE (ci);
-- Name: administrativos administrativos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.administrativos
    ADD CONSTRAINT administrativos_pkey PRIMARY KEY (id_administrativo);
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);
-- Name: alumnos alumno_ci_key; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.alumnos
    ADD CONSTRAINT alumno_ci_key UNIQUE (ci);
-- Name: alumnos alumno_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.alumnos
    ADD CONSTRAINT alumno_pkey PRIMARY KEY (id_alumno);
-- Name: certificados_notas certificados_notas_id_alumno_id_programa_version_edicion_key; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.certificados_notas
    ADD CONSTRAINT certificados_notas_id_alumno_id_programa_version_edicion_key UNIQUE (id_alumno, id_programa_version_edicion);
-- Name: certificados_notas certificados_notas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.certificados_notas
    ADD CONSTRAINT certificados_notas_pkey PRIMARY KEY (id_certificado);
-- Name: contratacion_docente contratacion_docente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.contratacion_docente
    ADD CONSTRAINT contratacion_docente_pkey PRIMARY KEY (id_contratacion);
-- Name: control_documentacion_contratacion control_documentacion_contratacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.control_documentacion_contratacion
    ADD CONSTRAINT control_documentacion_contratacion_pkey PRIMARY KEY (id_control_doc_contratacion);
-- Name: control_documentacion control_documentacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.control_documentacion
    ADD CONSTRAINT control_documentacion_pkey PRIMARY KEY (id_control_documentacion);
-- Name: detalle_programa_alumno detalle_programa_alumno_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.detalle_programa_alumno
    ADD CONSTRAINT detalle_programa_alumno_pkey PRIMARY KEY (id_detalle_programa_alumno);
-- Name: detalle_programa_modulo detalle_programa_modulo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.detalle_programa_modulo
    ADD CONSTRAINT detalle_programa_modulo_pkey PRIMARY KEY (id_detalle_programa_modulo);
-- Name: docentes docente_ci_key; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.docentes
    ADD CONSTRAINT docente_ci_key UNIQUE (ci);
-- Name: docentes docente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.docentes
    ADD CONSTRAINT docente_pkey PRIMARY KEY (id_docente);
-- Name: documento_solicitud documento_solicitud_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.documento_solicitud
    ADD CONSTRAINT documento_solicitud_pkey PRIMARY KEY (id_solicitud_documento);
-- Name: documentos_contratacion documentos_contratacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.documentos_contratacion
    ADD CONSTRAINT documentos_contratacion_pkey PRIMARY KEY (id_documento);
-- Name: etapa_contratacion etapa_contratacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.etapa_contratacion
    ADD CONSTRAINT etapa_contratacion_pkey PRIMARY KEY (id_etapa);
-- Name: etapa_requisito etapa_requisito_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.etapa_requisito
    ADD CONSTRAINT etapa_requisito_pkey PRIMARY KEY (id_etapa, id_requisito);
-- Name: historial_inscripcion historial_inscripcion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.historial_inscripcion
    ADD CONSTRAINT historial_inscripcion_pkey PRIMARY KEY (id_historial);
-- Name: historial_modulo historial_modulo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.historial_modulo
    ADD CONSTRAINT historial_modulo_pkey PRIMARY KEY (id_historial);
-- Name: horarios horario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.horarios
    ADD CONSTRAINT horario_pkey PRIMARY KEY (id_horario);
-- Name: informes_notas informes_notas_id_programa_version_edicion_numero_tanda_key; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.informes_notas
    ADD CONSTRAINT informes_notas_id_programa_version_edicion_numero_tanda_key UNIQUE (id_programa_version_edicion, numero_tanda);
-- Name: informes_notas informes_notas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.informes_notas
    ADD CONSTRAINT informes_notas_pkey PRIMARY KEY (id_informe);
-- Name: modalidades_academicas modalidad_academica_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modalidades_academicas
    ADD CONSTRAINT modalidad_academica_pkey PRIMARY KEY (id_modalidad_academica);
-- Name: modalidad_requisito modalidad_requisito_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modalidad_requisito
    ADD CONSTRAINT modalidad_requisito_pkey PRIMARY KEY (id_modalidad_academica, id_requisito);
-- Name: modalidad_tipo_descuento modalidad_tipo_descuento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modalidad_tipo_descuento
    ADD CONSTRAINT modalidad_tipo_descuento_pkey PRIMARY KEY (id_modalidad_academica, id_tipo_descuento);
-- Name: modalidad_tipo_programa modalidad_tipo_programa_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modalidad_tipo_programa
    ADD CONSTRAINT modalidad_tipo_programa_pkey PRIMARY KEY (id_modalidad_academica, id_tipo_programa);
-- Name: modulos modulo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modulos
    ADD CONSTRAINT modulo_pkey PRIMARY KEY (id_modulo);
-- Name: modulos modulos_sigla_key; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modulos
    ADD CONSTRAINT modulos_sigla_key UNIQUE (sigla);
-- Name: notas notas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.notas
    ADD CONSTRAINT notas_pkey PRIMARY KEY (id_nota);
-- Name: orden_pago orden_pago_numero_key; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.orden_pago
    ADD CONSTRAINT orden_pago_numero_key UNIQUE (numero);
-- Name: orden_pago orden_pago_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.orden_pago
    ADD CONSTRAINT orden_pago_pkey PRIMARY KEY (id_orden_pago);
-- Name: pagos pagos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.pagos
    ADD CONSTRAINT pagos_pkey PRIMARY KEY (id_pago);
-- Name: permisos permisos_codigo_key; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.permisos
    ADD CONSTRAINT permisos_codigo_key UNIQUE (codigo);
-- Name: permisos permisos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.permisos
    ADD CONSTRAINT permisos_pkey PRIMARY KEY (id_permiso);
-- Name: programas programa_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.programas
    ADD CONSTRAINT programa_pkey PRIMARY KEY (id_programa);
-- Name: programa_version_edicion programa_version_edicion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.programa_version_edicion
    ADD CONSTRAINT programa_version_edicion_pkey PRIMARY KEY (id_programa_version_edicion);
-- Name: programas_version programa_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.programas_version
    ADD CONSTRAINT programa_version_pkey PRIMARY KEY (id_programa_version);
-- Name: requisitos requisito_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.requisitos
    ADD CONSTRAINT requisito_pkey PRIMARY KEY (id_requisito);
-- Name: roles roles_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_nombre_key UNIQUE (nombre);
-- Name: roles_permisos roles_permisos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.roles_permisos
    ADD CONSTRAINT roles_permisos_pkey PRIMARY KEY (id_rol, id_permiso);
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id_rol);
-- Name: solicitud_incorporacion solicitud_incorporacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud_incorporacion
    ADD CONSTRAINT solicitud_incorporacion_pkey PRIMARY KEY (id_solicitud);
-- Name: solicitud_migracion solicitud_migracion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud_migracion
    ADD CONSTRAINT solicitud_migracion_pkey PRIMARY KEY (id_solicitud);
-- Name: solicitud solicitud_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud
    ADD CONSTRAINT solicitud_pkey PRIMARY KEY (id_solicitud);
-- Name: solicitud_requisito solicitud_requisito_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud_requisito
    ADD CONSTRAINT solicitud_requisito_pkey PRIMARY KEY (id_solicitud_requisito);
-- Name: tipo_solicitud solicitud_tipo_codigo_key; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.tipo_solicitud
    ADD CONSTRAINT solicitud_tipo_codigo_key UNIQUE (codigo);
-- Name: tipo_descuento_requisito tipo_descuento_requisito_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.tipo_descuento_requisito
    ADD CONSTRAINT tipo_descuento_requisito_pkey PRIMARY KEY (id_tipo_descuento, id_requisito);
-- Name: tipos_programa tipo_programa_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.tipos_programa
    ADD CONSTRAINT tipo_programa_pkey PRIMARY KEY (id_tipo_programa);
-- Name: tipo_solicitud tipo_solicitud_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.tipo_solicitud
    ADD CONSTRAINT tipo_solicitud_pkey PRIMARY KEY (id_tipo_solicitud);
-- Name: tipos_descuento tipos_descuento_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.tipos_descuento
    ADD CONSTRAINT tipos_descuento_nombre_key UNIQUE (nombre);
-- Name: tipos_descuento tipos_descuento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.tipos_descuento
    ADD CONSTRAINT tipos_descuento_pkey PRIMARY KEY (id_tipo_descuento);
-- Name: transaccion_pago transaccion_pago_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.transaccion_pago
    ADD CONSTRAINT transaccion_pago_pkey PRIMARY KEY (id_transaccion);
-- Name: detalle_programa_alumno uq_alumno_edicion; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.detalle_programa_alumno
    ADD CONSTRAINT uq_alumno_edicion UNIQUE (id_alumno, id_programa_version_edicion);
-- Name: alumnos uq_alumnos_correo; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.alumnos
    ADD CONSTRAINT uq_alumnos_correo UNIQUE (correo);
-- Name: alumnos uq_alumnos_pasaporte; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.alumnos
    ADD CONSTRAINT uq_alumnos_pasaporte UNIQUE (pasaporte);
-- Name: detalle_programa_modulo uq_detalle_orden_edicion; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.detalle_programa_modulo
    ADD CONSTRAINT uq_detalle_orden_edicion UNIQUE (id_programa_version_edicion, orden);
-- Name: usuarios uq_email; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT uq_email UNIQUE (email);
-- Name: modalidades_academicas uq_modalidades_academicas_nombre; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modalidades_academicas
    ADD CONSTRAINT uq_modalidades_academicas_nombre UNIQUE (nombre_modalidad);
-- Name: notas uq_nota_alumno_modulo; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.notas
    ADD CONSTRAINT uq_nota_alumno_modulo UNIQUE (id_detalle_programa_alumno, id_detalle_programa_modulo);
-- Name: programas_version uq_programa_version; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.programas_version
    ADD CONSTRAINT uq_programa_version UNIQUE (id_programa, version);
-- Name: programas uq_programas_nombre_programa; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.programas
    ADD CONSTRAINT uq_programas_nombre_programa UNIQUE (nombre_programa);
-- Name: requisitos uq_requisito_nombre; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.requisitos
    ADD CONSTRAINT uq_requisito_nombre UNIQUE (nombre);
-- Name: tipos_programa uq_tipos_programa_nombre; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.tipos_programa
    ADD CONSTRAINT uq_tipos_programa_nombre UNIQUE (nombre);
-- Name: usuario_roles usuario_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.usuario_roles
    ADD CONSTRAINT usuario_roles_pkey PRIMARY KEY (id_usuario, id_rol);
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id_usuario);
-- Name: idx_control_doc_contratacion_contratacion; Type: INDEX; Schema: public; Owner: -
CREATE INDEX idx_control_doc_contratacion_contratacion ON public.control_documentacion_contratacion USING btree (id_contratacion);
-- Name: idx_control_doc_contratacion_etapa; Type: INDEX; Schema: public; Owner: -
CREATE INDEX idx_control_doc_contratacion_etapa ON public.control_documentacion_contratacion USING btree (id_etapa);
-- Name: idx_control_doc_contratacion_requisito; Type: INDEX; Schema: public; Owner: -
CREATE INDEX idx_control_doc_contratacion_requisito ON public.control_documentacion_contratacion USING btree (id_requisito);
-- Name: idx_etapa_contratacion_tipo_programa; Type: INDEX; Schema: public; Owner: -
CREATE INDEX idx_etapa_contratacion_tipo_programa ON public.etapa_contratacion USING btree (id_tipo_programa);
-- Name: idx_historial_destino; Type: INDEX; Schema: public; Owner: -
CREATE INDEX idx_historial_destino ON public.historial_inscripcion USING btree (id_detalle_destino);
-- Name: idx_historial_origen; Type: INDEX; Schema: public; Owner: -
CREATE INDEX idx_historial_origen ON public.historial_inscripcion USING btree (id_detalle_origen);
-- Name: idx_solicitud_alumno; Type: INDEX; Schema: public; Owner: -
CREATE INDEX idx_solicitud_alumno ON public.solicitud USING btree (id_alumno);
-- Name: idx_solicitud_estado; Type: INDEX; Schema: public; Owner: -
CREATE INDEX idx_solicitud_estado ON public.solicitud USING btree (estado);
-- Name: idx_solicitud_requisito_estado; Type: INDEX; Schema: public; Owner: -
CREATE INDEX idx_solicitud_requisito_estado ON public.solicitud_requisito USING btree (estado);
-- Name: idx_solicitud_tipo; Type: INDEX; Schema: public; Owner: -
CREATE INDEX idx_solicitud_tipo ON public.solicitud USING btree (id_tipo_solicitud);
-- Name: ix_administrativos_id_administrativo; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_administrativos_id_administrativo ON public.administrativos USING btree (id_administrativo);
-- Name: ix_alumnos_id_alumno; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_alumnos_id_alumno ON public.alumnos USING btree (id_alumno);
-- Name: ix_contratacion_docente_id_contratacion; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_contratacion_docente_id_contratacion ON public.contratacion_docente USING btree (id_contratacion);
-- Name: ix_control_documentacion_id_control_documentacion; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_control_documentacion_id_control_documentacion ON public.control_documentacion USING btree (id_control_documentacion);
-- Name: ix_detalle_programa_alumno_id_detalle_programa_alumno; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_detalle_programa_alumno_id_detalle_programa_alumno ON public.detalle_programa_alumno USING btree (id_detalle_programa_alumno);
-- Name: ix_detalle_programa_modulo_id_detalle_programa_modulo; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_detalle_programa_modulo_id_detalle_programa_modulo ON public.detalle_programa_modulo USING btree (id_detalle_programa_modulo);
-- Name: ix_docentes_id_docente; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_docentes_id_docente ON public.docentes USING btree (id_docente);
-- Name: ix_documentos_contratacion_id_documento; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_documentos_contratacion_id_documento ON public.documentos_contratacion USING btree (id_documento);
-- Name: ix_historial_modulo_id_historial; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_historial_modulo_id_historial ON public.historial_modulo USING btree (id_historial);
-- Name: ix_horarios_id_horario; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_horarios_id_horario ON public.horarios USING btree (id_horario);
-- Name: ix_modalidades_academicas_id_modalidad_academica; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_modalidades_academicas_id_modalidad_academica ON public.modalidades_academicas USING btree (id_modalidad_academica);
-- Name: ix_modulos_id_modulo; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_modulos_id_modulo ON public.modulos USING btree (id_modulo);
-- Name: ix_notas_id_nota; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_notas_id_nota ON public.notas USING btree (id_nota);
-- Name: ix_orden_pago_estado; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_orden_pago_estado ON public.orden_pago USING btree (estado);
-- Name: ix_orden_pago_id_dpa; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_orden_pago_id_dpa ON public.orden_pago USING btree (id_detalle_programa_alumno);
-- Name: ix_pagos_id_pago; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_pagos_id_pago ON public.pagos USING btree (id_pago);
-- Name: ix_pagos_id_transaccion; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_pagos_id_transaccion ON public.pagos USING btree (id_transaccion);
-- Name: ix_permisos_id_permiso; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_permisos_id_permiso ON public.permisos USING btree (id_permiso);
-- Name: ix_programa_version_edicion_id_programa_version_edicion; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_programa_version_edicion_id_programa_version_edicion ON public.programa_version_edicion USING btree (id_programa_version_edicion);
-- Name: ix_programas_id_programa; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_programas_id_programa ON public.programas USING btree (id_programa);
-- Name: ix_programas_version_id_programa_version; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_programas_version_id_programa_version ON public.programas_version USING btree (id_programa_version);
-- Name: ix_requisitos_id_requisito; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_requisitos_id_requisito ON public.requisitos USING btree (id_requisito);
-- Name: ix_roles_id_rol; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_roles_id_rol ON public.roles USING btree (id_rol);
-- Name: ix_tipos_descuento_id_tipo_descuento; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_tipos_descuento_id_tipo_descuento ON public.tipos_descuento USING btree (id_tipo_descuento);
-- Name: ix_tipos_programa_id_tipo_programa; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_tipos_programa_id_tipo_programa ON public.tipos_programa USING btree (id_tipo_programa);
-- Name: ix_transaccion_pago_id_dpa; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_transaccion_pago_id_dpa ON public.transaccion_pago USING btree (id_detalle_programa_alumno);
-- Name: ix_transaccion_pago_id_orden_pago; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_transaccion_pago_id_orden_pago ON public.transaccion_pago USING btree (id_orden_pago);
-- Name: ix_usuarios_id_usuario; Type: INDEX; Schema: public; Owner: -
CREATE INDEX ix_usuarios_id_usuario ON public.usuarios USING btree (id_usuario);
-- Name: uq_contratacion_vigente; Type: INDEX; Schema: public; Owner: -
CREATE UNIQUE INDEX uq_contratacion_vigente ON public.contratacion_docente USING btree (id_detalle_modulo) WHERE ((estado)::text <> 'truncado'::text);
-- Name: administrativos administrativos_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.administrativos
    ADD CONSTRAINT administrativos_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuarios(id_usuario);
-- Name: alumnos alumnos_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.alumnos
    ADD CONSTRAINT alumnos_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuarios(id_usuario);
-- Name: certificados_notas certificados_notas_id_alumno_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.certificados_notas
    ADD CONSTRAINT certificados_notas_id_alumno_fkey FOREIGN KEY (id_alumno) REFERENCES public.alumnos(id_alumno);
-- Name: certificados_notas certificados_notas_id_informe_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.certificados_notas
    ADD CONSTRAINT certificados_notas_id_informe_fkey FOREIGN KEY (id_informe) REFERENCES public.informes_notas(id_informe);
-- Name: certificados_notas certificados_notas_id_programa_version_edicion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.certificados_notas
    ADD CONSTRAINT certificados_notas_id_programa_version_edicion_fkey FOREIGN KEY (id_programa_version_edicion) REFERENCES public.programa_version_edicion(id_programa_version_edicion);
-- Name: contratacion_docente contratacion_docente_id_detalle_modulo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.contratacion_docente
    ADD CONSTRAINT contratacion_docente_id_detalle_modulo_fkey FOREIGN KEY (id_detalle_modulo) REFERENCES public.detalle_programa_modulo(id_detalle_programa_modulo);
-- Name: contratacion_docente contratacion_docente_id_docente_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.contratacion_docente
    ADD CONSTRAINT contratacion_docente_id_docente_fkey FOREIGN KEY (id_docente) REFERENCES public.docentes(id_docente);
-- Name: contratacion_docente contratacion_docente_id_etapa_actual_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.contratacion_docente
    ADD CONSTRAINT contratacion_docente_id_etapa_actual_fkey FOREIGN KEY (id_etapa_actual) REFERENCES public.etapa_contratacion(id_etapa);
-- Name: control_documentacion_contratacion control_documentacion_contratacion_id_contratacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.control_documentacion_contratacion
    ADD CONSTRAINT control_documentacion_contratacion_id_contratacion_fkey FOREIGN KEY (id_contratacion) REFERENCES public.contratacion_docente(id_contratacion) ON DELETE CASCADE;
-- Name: control_documentacion_contratacion control_documentacion_contratacion_id_etapa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.control_documentacion_contratacion
    ADD CONSTRAINT control_documentacion_contratacion_id_etapa_fkey FOREIGN KEY (id_etapa) REFERENCES public.etapa_contratacion(id_etapa);
-- Name: control_documentacion_contratacion control_documentacion_contratacion_id_requisito_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.control_documentacion_contratacion
    ADD CONSTRAINT control_documentacion_contratacion_id_requisito_fkey FOREIGN KEY (id_requisito) REFERENCES public.requisitos(id_requisito);
-- Name: control_documentacion control_documentacion_id_detalle_programa_alumno_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.control_documentacion
    ADD CONSTRAINT control_documentacion_id_detalle_programa_alumno_fkey FOREIGN KEY (id_detalle_programa_alumno) REFERENCES public.detalle_programa_alumno(id_detalle_programa_alumno);
-- Name: control_documentacion control_documentacion_id_requisito_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.control_documentacion
    ADD CONSTRAINT control_documentacion_id_requisito_fkey FOREIGN KEY (id_requisito) REFERENCES public.requisitos(id_requisito);
-- Name: detalle_programa_alumno detalle_programa_alumno_id_alumno_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.detalle_programa_alumno
    ADD CONSTRAINT detalle_programa_alumno_id_alumno_fkey FOREIGN KEY (id_alumno) REFERENCES public.alumnos(id_alumno);
-- Name: detalle_programa_alumno detalle_programa_alumno_id_modalidad_academica_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.detalle_programa_alumno
    ADD CONSTRAINT detalle_programa_alumno_id_modalidad_academica_fkey FOREIGN KEY (id_modalidad_academica) REFERENCES public.modalidades_academicas(id_modalidad_academica);
-- Name: detalle_programa_alumno detalle_programa_alumno_id_modulo_inicio_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.detalle_programa_alumno
    ADD CONSTRAINT detalle_programa_alumno_id_modulo_inicio_fkey FOREIGN KEY (id_modulo_inicio) REFERENCES public.detalle_programa_modulo(id_detalle_programa_modulo);
-- Name: detalle_programa_alumno detalle_programa_alumno_id_programa_version_edicion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.detalle_programa_alumno
    ADD CONSTRAINT detalle_programa_alumno_id_programa_version_edicion_fkey FOREIGN KEY (id_programa_version_edicion) REFERENCES public.programa_version_edicion(id_programa_version_edicion);
-- Name: detalle_programa_alumno detalle_programa_alumno_id_tipo_descuento_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.detalle_programa_alumno
    ADD CONSTRAINT detalle_programa_alumno_id_tipo_descuento_fkey FOREIGN KEY (id_tipo_descuento) REFERENCES public.tipos_descuento(id_tipo_descuento);
-- Name: detalle_programa_modulo detalle_programa_modulo_id_modulo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.detalle_programa_modulo
    ADD CONSTRAINT detalle_programa_modulo_id_modulo_fkey FOREIGN KEY (id_modulo) REFERENCES public.modulos(id_modulo);
-- Name: detalle_programa_modulo detalle_programa_modulo_id_programa_version_edicion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.detalle_programa_modulo
    ADD CONSTRAINT detalle_programa_modulo_id_programa_version_edicion_fkey FOREIGN KEY (id_programa_version_edicion) REFERENCES public.programa_version_edicion(id_programa_version_edicion);
-- Name: docentes docentes_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.docentes
    ADD CONSTRAINT docentes_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuarios(id_usuario);
-- Name: documentos_contratacion documentos_contratacion_id_contratacion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.documentos_contratacion
    ADD CONSTRAINT documentos_contratacion_id_contratacion_fkey FOREIGN KEY (id_contratacion) REFERENCES public.contratacion_docente(id_contratacion);
-- Name: etapa_contratacion etapa_contratacion_id_tipo_programa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.etapa_contratacion
    ADD CONSTRAINT etapa_contratacion_id_tipo_programa_fkey FOREIGN KEY (id_tipo_programa) REFERENCES public.tipos_programa(id_tipo_programa);
-- Name: etapa_requisito etapa_requisito_id_etapa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.etapa_requisito
    ADD CONSTRAINT etapa_requisito_id_etapa_fkey FOREIGN KEY (id_etapa) REFERENCES public.etapa_contratacion(id_etapa) ON DELETE CASCADE;
-- Name: etapa_requisito etapa_requisito_id_requisito_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.etapa_requisito
    ADD CONSTRAINT etapa_requisito_id_requisito_fkey FOREIGN KEY (id_requisito) REFERENCES public.requisitos(id_requisito);
-- Name: documento_solicitud fk_doc_solicitud_requisito; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.documento_solicitud
    ADD CONSTRAINT fk_doc_solicitud_requisito FOREIGN KEY (id_requisito) REFERENCES public.requisitos(id_requisito);
-- Name: documento_solicitud fk_doc_solicitud_solicitud; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.documento_solicitud
    ADD CONSTRAINT fk_doc_solicitud_solicitud FOREIGN KEY (id_solicitud) REFERENCES public.solicitud(id_solicitud);
-- Name: solicitud fk_solicitud_tipo; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud
    ADD CONSTRAINT fk_solicitud_tipo FOREIGN KEY (id_tipo_solicitud) REFERENCES public.tipo_solicitud(id_tipo_solicitud);
-- Name: historial_inscripcion historial_inscripcion_id_detalle_destino_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.historial_inscripcion
    ADD CONSTRAINT historial_inscripcion_id_detalle_destino_fkey FOREIGN KEY (id_detalle_destino) REFERENCES public.detalle_programa_alumno(id_detalle_programa_alumno);
-- Name: historial_inscripcion historial_inscripcion_id_detalle_origen_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.historial_inscripcion
    ADD CONSTRAINT historial_inscripcion_id_detalle_origen_fkey FOREIGN KEY (id_detalle_origen) REFERENCES public.detalle_programa_alumno(id_detalle_programa_alumno);
-- Name: historial_inscripcion historial_inscripcion_id_solicitud_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.historial_inscripcion
    ADD CONSTRAINT historial_inscripcion_id_solicitud_fkey FOREIGN KEY (id_solicitud) REFERENCES public.solicitud(id_solicitud);
-- Name: historial_modulo historial_modulo_id_detalle_programa_modulo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.historial_modulo
    ADD CONSTRAINT historial_modulo_id_detalle_programa_modulo_fkey FOREIGN KEY (id_detalle_programa_modulo) REFERENCES public.detalle_programa_modulo(id_detalle_programa_modulo);
-- Name: horarios horario_id_detalle_programa_modulo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.horarios
    ADD CONSTRAINT horario_id_detalle_programa_modulo_fkey FOREIGN KEY (id_detalle_programa_modulo) REFERENCES public.detalle_programa_modulo(id_detalle_programa_modulo);
-- Name: informes_notas informes_notas_id_programa_version_edicion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.informes_notas
    ADD CONSTRAINT informes_notas_id_programa_version_edicion_fkey FOREIGN KEY (id_programa_version_edicion) REFERENCES public.programa_version_edicion(id_programa_version_edicion);
-- Name: modalidad_requisito modalidad_requisito_id_modalidad_academica_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modalidad_requisito
    ADD CONSTRAINT modalidad_requisito_id_modalidad_academica_fkey FOREIGN KEY (id_modalidad_academica) REFERENCES public.modalidades_academicas(id_modalidad_academica);
-- Name: modalidad_requisito modalidad_requisito_id_requisito_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modalidad_requisito
    ADD CONSTRAINT modalidad_requisito_id_requisito_fkey FOREIGN KEY (id_requisito) REFERENCES public.requisitos(id_requisito);
-- Name: modalidad_tipo_descuento modalidad_tipo_descuento_id_modalidad_academica_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modalidad_tipo_descuento
    ADD CONSTRAINT modalidad_tipo_descuento_id_modalidad_academica_fkey FOREIGN KEY (id_modalidad_academica) REFERENCES public.modalidades_academicas(id_modalidad_academica);
-- Name: modalidad_tipo_descuento modalidad_tipo_descuento_id_tipo_descuento_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modalidad_tipo_descuento
    ADD CONSTRAINT modalidad_tipo_descuento_id_tipo_descuento_fkey FOREIGN KEY (id_tipo_descuento) REFERENCES public.tipos_descuento(id_tipo_descuento);
-- Name: modalidad_tipo_programa modalidad_tipo_programa_id_modalidad_academica_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modalidad_tipo_programa
    ADD CONSTRAINT modalidad_tipo_programa_id_modalidad_academica_fkey FOREIGN KEY (id_modalidad_academica) REFERENCES public.modalidades_academicas(id_modalidad_academica);
-- Name: modalidad_tipo_programa modalidad_tipo_programa_id_tipo_programa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modalidad_tipo_programa
    ADD CONSTRAINT modalidad_tipo_programa_id_tipo_programa_fkey FOREIGN KEY (id_tipo_programa) REFERENCES public.tipos_programa(id_tipo_programa);
-- Name: modulos modulo_id_programa_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.modulos
    ADD CONSTRAINT modulo_id_programa_version_fkey FOREIGN KEY (id_programa_version) REFERENCES public.programas_version(id_programa_version);
-- Name: notas notas_id_detalle_programa_alumno_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.notas
    ADD CONSTRAINT notas_id_detalle_programa_alumno_fkey FOREIGN KEY (id_detalle_programa_alumno) REFERENCES public.detalle_programa_alumno(id_detalle_programa_alumno);
-- Name: notas notas_id_detalle_programa_modulo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.notas
    ADD CONSTRAINT notas_id_detalle_programa_modulo_fkey FOREIGN KEY (id_detalle_programa_modulo) REFERENCES public.detalle_programa_modulo(id_detalle_programa_modulo);
-- Name: orden_pago orden_pago_anulado_por_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.orden_pago
    ADD CONSTRAINT orden_pago_anulado_por_id_usuario_fkey FOREIGN KEY (anulado_por_id_usuario) REFERENCES public.usuarios(id_usuario);
-- Name: orden_pago orden_pago_creado_por_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.orden_pago
    ADD CONSTRAINT orden_pago_creado_por_id_usuario_fkey FOREIGN KEY (creado_por_id_usuario) REFERENCES public.usuarios(id_usuario);
-- Name: orden_pago orden_pago_id_detalle_programa_alumno_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.orden_pago
    ADD CONSTRAINT orden_pago_id_detalle_programa_alumno_fkey FOREIGN KEY (id_detalle_programa_alumno) REFERENCES public.detalle_programa_alumno(id_detalle_programa_alumno);
-- Name: pagos pagos_id_detalle_programa_modulo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.pagos
    ADD CONSTRAINT pagos_id_detalle_programa_modulo_fkey FOREIGN KEY (id_detalle_programa_modulo) REFERENCES public.detalle_programa_modulo(id_detalle_programa_modulo);
-- Name: pagos pagos_id_transaccion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.pagos
    ADD CONSTRAINT pagos_id_transaccion_fkey FOREIGN KEY (id_transaccion) REFERENCES public.transaccion_pago(id_transaccion);
-- Name: programas programa_id_tipo_programa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.programas
    ADD CONSTRAINT programa_id_tipo_programa_fkey FOREIGN KEY (id_tipo_programa) REFERENCES public.tipos_programa(id_tipo_programa);
-- Name: programa_version_edicion programa_version_edicion_id_programa_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.programa_version_edicion
    ADD CONSTRAINT programa_version_edicion_id_programa_version_fkey FOREIGN KEY (id_programa_version) REFERENCES public.programas_version(id_programa_version);
-- Name: programas_version programa_version_id_programa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.programas_version
    ADD CONSTRAINT programa_version_id_programa_fkey FOREIGN KEY (id_programa) REFERENCES public.programas(id_programa);
-- Name: roles_permisos roles_permisos_id_permiso_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.roles_permisos
    ADD CONSTRAINT roles_permisos_id_permiso_fkey FOREIGN KEY (id_permiso) REFERENCES public.permisos(id_permiso);
-- Name: roles_permisos roles_permisos_id_rol_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.roles_permisos
    ADD CONSTRAINT roles_permisos_id_rol_fkey FOREIGN KEY (id_rol) REFERENCES public.roles(id_rol);
-- Name: solicitud solicitud_id_alumno_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud
    ADD CONSTRAINT solicitud_id_alumno_fkey FOREIGN KEY (id_alumno) REFERENCES public.alumnos(id_alumno);
-- Name: solicitud solicitud_id_detalle_origen_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud
    ADD CONSTRAINT solicitud_id_detalle_origen_fkey FOREIGN KEY (id_detalle_origen) REFERENCES public.detalle_programa_alumno(id_detalle_programa_alumno);
-- Name: solicitud_incorporacion solicitud_incorporacion_id_modalidad_academica_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud_incorporacion
    ADD CONSTRAINT solicitud_incorporacion_id_modalidad_academica_fkey FOREIGN KEY (id_modalidad_academica) REFERENCES public.modalidades_academicas(id_modalidad_academica);
-- Name: solicitud_incorporacion solicitud_incorporacion_id_programa_version_edicion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud_incorporacion
    ADD CONSTRAINT solicitud_incorporacion_id_programa_version_edicion_fkey FOREIGN KEY (id_programa_version_edicion) REFERENCES public.programa_version_edicion(id_programa_version_edicion);
-- Name: solicitud_incorporacion solicitud_incorporacion_id_solicitud_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud_incorporacion
    ADD CONSTRAINT solicitud_incorporacion_id_solicitud_fkey FOREIGN KEY (id_solicitud) REFERENCES public.solicitud(id_solicitud);
-- Name: solicitud_incorporacion solicitud_incorporacion_id_tipo_descuento_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud_incorporacion
    ADD CONSTRAINT solicitud_incorporacion_id_tipo_descuento_fkey FOREIGN KEY (id_tipo_descuento) REFERENCES public.tipos_descuento(id_tipo_descuento);
-- Name: solicitud_migracion solicitud_migracion_id_edicion_destino_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud_migracion
    ADD CONSTRAINT solicitud_migracion_id_edicion_destino_fkey FOREIGN KEY (id_edicion_destino) REFERENCES public.programa_version_edicion(id_programa_version_edicion);
-- Name: solicitud_migracion solicitud_migracion_id_solicitud_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud_migracion
    ADD CONSTRAINT solicitud_migracion_id_solicitud_fkey FOREIGN KEY (id_solicitud) REFERENCES public.solicitud(id_solicitud);
-- Name: solicitud_requisito solicitud_requisito_id_requisito_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud_requisito
    ADD CONSTRAINT solicitud_requisito_id_requisito_fkey FOREIGN KEY (id_requisito) REFERENCES public.requisitos(id_requisito);
-- Name: solicitud_requisito solicitud_requisito_id_tipo_solicitud_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.solicitud_requisito
    ADD CONSTRAINT solicitud_requisito_id_tipo_solicitud_fkey FOREIGN KEY (id_tipo_solicitud) REFERENCES public.tipo_solicitud(id_tipo_solicitud);
-- Name: tipo_descuento_requisito tipo_descuento_requisito_id_requisito_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.tipo_descuento_requisito
    ADD CONSTRAINT tipo_descuento_requisito_id_requisito_fkey FOREIGN KEY (id_requisito) REFERENCES public.requisitos(id_requisito);
-- Name: tipo_descuento_requisito tipo_descuento_requisito_id_tipo_descuento_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.tipo_descuento_requisito
    ADD CONSTRAINT tipo_descuento_requisito_id_tipo_descuento_fkey FOREIGN KEY (id_tipo_descuento) REFERENCES public.tipos_descuento(id_tipo_descuento);
-- Name: transaccion_pago transaccion_pago_anulado_por_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.transaccion_pago
    ADD CONSTRAINT transaccion_pago_anulado_por_id_usuario_fkey FOREIGN KEY (anulado_por_id_usuario) REFERENCES public.usuarios(id_usuario);
-- Name: transaccion_pago transaccion_pago_creado_por_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.transaccion_pago
    ADD CONSTRAINT transaccion_pago_creado_por_id_usuario_fkey FOREIGN KEY (creado_por_id_usuario) REFERENCES public.usuarios(id_usuario);
-- Name: transaccion_pago transaccion_pago_id_detalle_programa_alumno_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.transaccion_pago
    ADD CONSTRAINT transaccion_pago_id_detalle_programa_alumno_fkey FOREIGN KEY (id_detalle_programa_alumno) REFERENCES public.detalle_programa_alumno(id_detalle_programa_alumno);
-- Name: transaccion_pago transaccion_pago_id_orden_pago_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.transaccion_pago
    ADD CONSTRAINT transaccion_pago_id_orden_pago_fkey FOREIGN KEY (id_orden_pago) REFERENCES public.orden_pago(id_orden_pago);
-- Name: usuario_roles usuario_roles_id_rol_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.usuario_roles
    ADD CONSTRAINT usuario_roles_id_rol_fkey FOREIGN KEY (id_rol) REFERENCES public.roles(id_rol);
-- Name: usuario_roles usuario_roles_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
ALTER TABLE ONLY public.usuario_roles
    ADD CONSTRAINT usuario_roles_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuarios(id_usuario);
-- PostgreSQL database dump complete
\unrestrict UgsWfXu0SgiaNjMwiJ5qgkLt6mC3NyAcAemvgmHojOPAOaUcflViLoYdv2ISjHD
