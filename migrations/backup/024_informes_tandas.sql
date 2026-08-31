-- Las tandas pasan a ser lotes de alumnos del informe final (varios finales por edición).
-- Los borradores dejan de numerar tanda (NULL; en Postgres NULL no choca con el unique).
ALTER TABLE informes_notas ALTER COLUMN numero_tanda DROP NOT NULL;

-- Nombre del emisor en orden natural (Nombre Apellido), no "Apellido, Nombre".
UPDATE informes_notas SET emitido_por_nombre = 'Julio Toledo'
WHERE emitido_por_nombre = 'Toledo, Julio';