-- 022: certificados de notas individuales por edición, fuera de la modalidad Educación Continua.
-- Los certificados pueden emitirse en el informe final (procedencia 'informe', incluida EC)
-- o individualmente por el administrativo académico (procedencia 'individual', excluye EC).

ALTER TABLE certificados_notas ALTER COLUMN id_informe DROP NOT NULL;

ALTER TABLE certificados_notas ADD COLUMN emitido_por INTEGER REFERENCES usuarios(id_usuario);
ALTER TABLE certificados_notas ADD COLUMN emitido_at TIMESTAMPTZ;
ALTER TABLE certificados_notas ADD COLUMN datos JSONB;
ALTER TABLE certificados_notas ADD COLUMN procedencia VARCHAR(20) NOT NULL DEFAULT 'informe';
ALTER TABLE certificados_notas ADD COLUMN numero_certificado INTEGER;
ALTER TABLE certificados_notas ADD COLUMN codigo VARCHAR(30);
ALTER TABLE certificados_notas ADD COLUMN n_impresiones INTEGER NOT NULL DEFAULT 0;
ALTER TABLE certificados_notas ADD COLUMN ultima_impresion_at TIMESTAMPTZ;

-- Número secuencial por edición de programa
CREATE UNIQUE INDEX uq_certificado_numero_edicion ON certificados_notas (id_programa_version_edicion, numero_certificado);