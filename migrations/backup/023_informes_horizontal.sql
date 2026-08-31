-- Migración 023: Informes de notas horizontales (matriz por carrera) + autoría
-- 1. Se eliminan los informes parciales con formato viejo (tablas por módulo, sin matriz) — solo datos de prueba
-- 2. tipo pasa de 'parcial' a 'borrador' (valores: borrador|final)
-- 3. informes_notas gana emitido_por (FK usuarios) + emitido_por_nombre (snapshot del autor)

DELETE FROM certificados_notas
WHERE id_informe IN (SELECT id_informe FROM informes_notas WHERE tipo = 'parcial');

DELETE FROM informes_notas WHERE tipo = 'parcial';

ALTER TABLE informes_notas
    ALTER COLUMN tipo DROP DEFAULT;

UPDATE informes_notas SET tipo = 'borrador' WHERE tipo = 'parcial';

ALTER TABLE informes_notas
    ALTER COLUMN tipo SET DEFAULT 'borrador';

ALTER TABLE informes_notas
    ADD COLUMN IF NOT EXISTS emitido_por INT REFERENCES usuarios(id_usuario),
    ADD COLUMN IF NOT EXISTS emitido_por_nombre VARCHAR(120);