-- Programa versión edición: costo de matrícula configurable (cuota aparte del precio del programa).
ALTER TABLE programa_version_edicion ADD COLUMN IF NOT EXISTS matricula DOUBLE PRECISION NOT NULL DEFAULT 0;

-- Backfill: las ediciones existentes ya tienen la matrícula legacy normalizada a 200 Bs (migración 009).
UPDATE programa_version_edicion SET matricula = 200 WHERE matricula = 0;
