-- Migración 020: Eliminar columna obligatorio de etapa_requisito
-- Si un requisito está en una etapa, es obligatorio. No hay caso de uso donde no lo sea.

ALTER TABLE etapa_requisito DROP COLUMN IF EXISTS obligatorio;
