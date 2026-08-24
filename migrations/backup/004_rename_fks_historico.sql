BEGIN;

-- 1. Rename tables
ALTER TABLE solicitud_tipo RENAME TO tipo_solicitud;
ALTER TABLE solicitud_documento RENAME TO documento_solicitud;

-- 2. Rename sequences
ALTER SEQUENCE solicitud_tipo_id_solicitud_tipo_seq RENAME TO tipo_solicitud_id_solicitud_tipo_seq;
ALTER SEQUENCE solicitud_documento_id_solicitud_documento_seq RENAME TO documento_solicitud_id_documento_solicitud_seq;

-- 3. Rename PK constraint on tipo_solicitud
ALTER TABLE tipo_solicitud RENAME CONSTRAINT solicitud_tipo_pkey TO tipo_solicitud_pkey;

-- 4. Rename PK constraint on documento_solicitud
ALTER TABLE documento_solicitud RENAME CONSTRAINT solicitud_documento_pkey TO documento_solicitud_pkey;

-- 5. Rename FK constraints on solicitud (references tipo_solicitud now)
ALTER TABLE solicitud RENAME CONSTRAINT solicitud_id_tipo_solicitud_fkey TO fk_solicitud_tipo;

-- 6. Rename FKs on documento_solicitud (references solicitud, requisitos)
ALTER TABLE documento_solicitud RENAME CONSTRAINT solicitud_documento_id_solicitud_fkey TO fk_doc_solicitud_solicitud;
ALTER TABLE documento_solicitud RENAME CONSTRAINT solicitud_documento_id_requisito_fkey TO fk_doc_solicitud_requisito;

-- 7. Add id_modulo_inicio FK to detalle_programa_alumno
ALTER TABLE detalle_programa_alumno ADD COLUMN id_modulo_inicio INTEGER REFERENCES detalle_programa_modulo(id_detalle_programa_modulo);

-- 8. Add id_modulo_inicio FK to solicitud
ALTER TABLE solicitud ADD COLUMN id_modulo_inicio INTEGER REFERENCES detalle_programa_modulo(id_detalle_programa_modulo);

-- 9. Migrate existing data for detalle_programa_alumno
UPDATE detalle_programa_alumno dpa
SET id_modulo_inicio = (
    SELECT dpm.id_detalle_programa_modulo
    FROM detalle_programa_modulo dpm
    WHERE dpm.id_programa_version_edicion = dpa.id_programa_version_edicion
    AND dpm.orden = dpa.modulo_inicio
    LIMIT 1
);

-- 10. Migrate existing data for solicitud
UPDATE solicitud s
SET id_modulo_inicio = (
    SELECT dpm.id_detalle_programa_modulo
    FROM detalle_programa_modulo dpm
    WHERE dpm.id_programa_version_edicion = s.id_programa_version_edicion
    AND dpm.orden = s.modulo_inicio
    LIMIT 1
);

-- 11. historial_inscripcion: delete orphans + make id_solicitud NOT NULL
DELETE FROM historial_inscripcion WHERE id_solicitud IS NULL;
ALTER TABLE historial_inscripcion ALTER COLUMN id_solicitud SET NOT NULL;

COMMIT;
