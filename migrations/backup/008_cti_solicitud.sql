-- Class Table Inheritance: mover columnas específicas a subtablas
-- Incorporación tiene edición+modalidad propias (elegidas por alumno)
-- Migración tiene edición destino+motivo propios (decididos por admin)
-- Reincorporación no necesita subtabla (todo se deriva del DPA origen)
-- Modalidad académica en migración se hereda del DPA origen, no se almacena

BEGIN;

CREATE TABLE solicitud_incorporacion (
    id_solicitud INTEGER PRIMARY KEY REFERENCES solicitud(id_solicitud),
    id_programa_version_edicion INTEGER NOT NULL REFERENCES programa_version_edicion(id_programa_version_edicion),
    id_modalidad_academica INTEGER NOT NULL REFERENCES modalidades_academicas(id_modalidad_academica),
    id_tipo_descuento INTEGER REFERENCES tipos_descuento(id_tipo_descuento)
);

CREATE TABLE solicitud_migracion (
    id_solicitud INTEGER PRIMARY KEY REFERENCES solicitud(id_solicitud),
    id_edicion_destino INTEGER NOT NULL REFERENCES programa_version_edicion(id_programa_version_edicion),
    motivo TEXT NOT NULL DEFAULT ''
);

INSERT INTO solicitud_incorporacion (id_solicitud, id_programa_version_edicion, id_modalidad_academica, id_tipo_descuento)
SELECT id_solicitud, id_programa_version_edicion, id_modalidad_academica, id_tipo_descuento
FROM solicitud
WHERE id_programa_version_edicion IS NOT NULL
  AND id_tipo_solicitud = (SELECT id_tipo_solicitud FROM tipo_solicitud WHERE codigo = 'incorporacion');

INSERT INTO solicitud_migracion (id_solicitud, id_edicion_destino, motivo)
SELECT id_solicitud, id_programa_version_edicion, COALESCE(motivo, '')
FROM solicitud
WHERE id_programa_version_edicion IS NOT NULL
  AND id_tipo_solicitud = (SELECT id_tipo_solicitud FROM tipo_solicitud WHERE codigo = 'migracion');

ALTER TABLE solicitud DROP CONSTRAINT IF EXISTS solicitud_id_modulo_inicio_fkey;
ALTER TABLE solicitud DROP CONSTRAINT IF EXISTS solicitud_id_programa_version_edicion_fkey;
ALTER TABLE solicitud DROP CONSTRAINT IF EXISTS solicitud_id_modalidad_academica_fkey;
ALTER TABLE solicitud DROP CONSTRAINT IF EXISTS solicitud_id_tipo_descuento_fkey;

ALTER TABLE solicitud
    DROP COLUMN id_programa_version_edicion,
    DROP COLUMN id_modalidad_academica,
    DROP COLUMN id_tipo_descuento,
    DROP COLUMN modulo_inicio,
    DROP COLUMN id_modulo_inicio;

COMMIT;
