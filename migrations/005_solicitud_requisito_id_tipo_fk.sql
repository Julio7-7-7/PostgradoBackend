BEGIN;

ALTER TABLE solicitud_requisito ADD COLUMN id_tipo_solicitud INTEGER REFERENCES tipo_solicitud(id_solicitud_tipo);

UPDATE solicitud_requisito
SET id_tipo_solicitud = ts.id_solicitud_tipo
FROM tipo_solicitud ts
WHERE ts.codigo = solicitud_requisito.tipo;

ALTER TABLE solicitud_requisito ALTER COLUMN id_tipo_solicitud SET NOT NULL;
ALTER TABLE solicitud_requisito DROP COLUMN tipo;

-- documento_solicitud.fecha_entrega nullable (se setea al subir archivo, no al crear)
ALTER TABLE documento_solicitud ALTER COLUMN fecha_entrega DROP DEFAULT;
ALTER TABLE documento_solicitud ALTER COLUMN fecha_entrega DROP NOT NULL;

COMMIT;
