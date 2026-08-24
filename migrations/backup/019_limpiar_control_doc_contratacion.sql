-- Migración 019: Limpiar columnas obsoletas de control_documentacion_contratacion
-- fecha_entrega y fecha_revision se eliminan (el admin no "entrega" ni "revisa" en ese sentido)
-- observaciones se renombra a notas

ALTER TABLE control_documentacion_contratacion
  DROP COLUMN IF EXISTS fecha_entrega,
  DROP COLUMN IF EXISTS fecha_revision;

-- Renombrar observaciones a notas si existe la columna
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'control_documentacion_contratacion' AND column_name = 'observaciones') THEN
    ALTER TABLE control_documentacion_contratacion RENAME COLUMN observaciones TO notas;
  END IF;
END $$;
