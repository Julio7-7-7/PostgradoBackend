BEGIN;

-- 1. Catalog table for solicitud tipos
CREATE TABLE solicitud_tipo (
    id_solicitud_tipo SERIAL PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL
);

INSERT INTO solicitud_tipo (codigo, nombre) VALUES
    ('incorporacion', 'Incorporación'),
    ('migracion', 'Migración'),
    ('reincorporacion', 'Reincorporación');

-- 2. Unified solicitud table
CREATE TABLE solicitud (
    id_solicitud SERIAL PRIMARY KEY,
    id_tipo_solicitud INTEGER NOT NULL REFERENCES solicitud_tipo(id_solicitud_tipo),
    id_alumno INTEGER NOT NULL REFERENCES alumnos(id_alumno),
    id_detalle_origen INTEGER REFERENCES detalle_programa_alumno(id_detalle_programa_alumno),
    id_programa_version_edicion INTEGER REFERENCES programa_version_edicion(id_programa_version_edicion),
    id_modalidad_academica INTEGER REFERENCES modalidades_academicas(id_modalidad_academica),
    id_tipo_descuento INTEGER REFERENCES tipos_descuento(id_tipo_descuento),
    modulo_inicio INTEGER NOT NULL DEFAULT 1,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    motivo TEXT,
    motivo_rechazo TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_solicitud_alumno ON solicitud(id_alumno);
CREATE INDEX idx_solicitud_tipo ON solicitud(id_tipo_solicitud);
CREATE INDEX idx_solicitud_estado ON solicitud(estado);

-- 3. Migrate solicitud_incorporacion → solicitud (tipo: incorporacion)
INSERT INTO solicitud (
    id_solicitud, id_tipo_solicitud, id_alumno,
    id_detalle_origen, id_programa_version_edicion,
    id_modalidad_academica, id_tipo_descuento, modulo_inicio,
    estado, motivo_rechazo, created_at, updated_at
)
SELECT
    si.id_solicitud,
    st.id_solicitud_tipo,
    COALESCE(dpa.id_alumno, 0),
    si.id_detalle_programa_alumno,
    si.id_programa_version_edicion,
    dpa.id_modalidad_academica,
    dpa.id_tipo_descuento,
    COALESCE(dpa.modulo_inicio, 1),
    CASE WHEN si.estado = 'aceptado' THEN 'aprobado' ELSE si.estado END,
    CASE WHEN si.estado = 'rechazado' THEN si.observaciones ELSE NULL END,
    si.created_at,
    si.updated_at
FROM solicitud_incorporacion si
LEFT JOIN detalle_programa_alumno dpa ON si.id_detalle_programa_alumno = dpa.id_detalle_programa_alumno
CROSS JOIN LATERAL (SELECT id_solicitud_tipo FROM solicitud_tipo WHERE codigo = 'incorporacion') st;

-- 4. Migrate solicitud_reincorporacion → solicitud (tipo: reincorporacion)
INSERT INTO solicitud (
    id_solicitud, id_tipo_solicitud, id_alumno,
    id_detalle_origen, id_programa_version_edicion,
    estado, motivo, motivo_rechazo, created_at, updated_at
)
SELECT
    sr.id_solicitud_reincorporacion + 1000,
    st.id_solicitud_tipo,
    dpa.id_alumno,
    sr.id_detalle_programa_alumno,
    dpa.id_programa_version_edicion,
    CASE WHEN sr.estado = 'aprobada' THEN 'aprobado' ELSE sr.estado END,
    sr.motivo,
    sr.motivo_rechazo,
    sr.created_at,
    sr.updated_at
FROM solicitud_reincorporacion sr
JOIN detalle_programa_alumno dpa ON sr.id_detalle_programa_alumno = dpa.id_detalle_programa_alumno
CROSS JOIN LATERAL (SELECT id_solicitud_tipo FROM solicitud_tipo WHERE codigo = 'reincorporacion') st;

-- 5. Drop old FKs
ALTER TABLE solicitud_documento DROP CONSTRAINT IF EXISTS solicitud_documento_id_solicitud_fkey;
ALTER TABLE historial_inscripcion DROP CONSTRAINT IF EXISTS historial_inscripcion_id_solicitud_fkey;
ALTER TABLE solicitud_reincorporacion_documento DROP CONSTRAINT IF EXISTS solicitud_reincorporacion_doc_id_solicitud_reincorporacion_fkey;

-- 6. Add new FK on solicitud_documento → solicitud
ALTER TABLE solicitud_documento
    ADD CONSTRAINT solicitud_documento_id_solicitud_fkey
    FOREIGN KEY (id_solicitud) REFERENCES solicitud(id_solicitud);

-- 7. Add new FK on historial_inscripcion → solicitud
ALTER TABLE historial_inscripcion
    ADD CONSTRAINT historial_inscripcion_id_solicitud_fkey
    FOREIGN KEY (id_solicitud) REFERENCES solicitud(id_solicitud);

-- 8. Drop old tables (order matters for FK deps)
DROP TABLE IF EXISTS solicitud_reincorporacion_documento;
DROP TABLE IF EXISTS solicitud_reincorporacion;
DROP TABLE IF EXISTS solicitud_incorporacion;

-- 9. Drop unused sequences
DROP SEQUENCE IF EXISTS documento_incorporacion_id_documento_incorporacion_seq;
DROP SEQUENCE IF EXISTS solicitud_reincorporacion_id_solicitud_reincorporacion_seq;

-- 10. Set the solicitud sequence past the max id
SELECT setval('solicitud_id_solicitud_seq', COALESCE((SELECT MAX(id_solicitud) FROM solicitud) + 1, 1), false);

-- 11. Add migracion requisitos to solicitud_requisito (reuse Carta de Solicitud)
INSERT INTO solicitud_requisito (id_requisito, obligatorio, tipo)
SELECT id_requisito, true, 'migracion'
FROM requisitos
WHERE id_requisito = 6  -- Carta de Solicitud de Incorporación (reused for migración)
AND NOT EXISTS (
    SELECT 1 FROM solicitud_requisito WHERE tipo = 'migracion' AND id_requisito = 6
);

COMMIT;
