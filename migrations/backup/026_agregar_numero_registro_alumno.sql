-- 026_agregar_numero_registro_alumno.sql
-- Agrega el campo opcional "número de registro" a la tabla alumnos.
-- Se usa en el informe de notas para identificar a los estudiantes de
-- Educación Continua (que pueden no tener CI/pasaporte) en lugar del CI.

BEGIN;

ALTER TABLE alumnos
  ADD COLUMN IF NOT EXISTS numero_registro VARCHAR(30) NULL;

COMMIT;
