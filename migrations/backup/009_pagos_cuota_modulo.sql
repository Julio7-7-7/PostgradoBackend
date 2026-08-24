-- Pagos: vínculo pago <-> cuota (módulo de la edición). NULL = matrícula.
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS id_detalle_programa_modulo INTEGER REFERENCES detalle_programa_modulo(id_detalle_programa_modulo);

-- Backfill legacy: "Cuota N Ed.X" -> módulo con orden N en la edición del pago
UPDATE pagos p
SET id_detalle_programa_modulo = dpm.id_detalle_programa_modulo
FROM detalle_programa_alumno dpa
JOIN detalle_programa_modulo dpm
  ON dpm.id_programa_version_edicion = dpa.id_programa_version_edicion
WHERE p.id_detalle_programa_alumno = dpa.id_detalle_programa_alumno
  AND p.id_detalle_programa_modulo IS NULL
  AND p.concepto ~ '^Cuota[[:space:]]+([0-9]+)'
  AND dpm.orden = CAST((regexp_match(p.concepto, '^Cuota[[:space:]]+([0-9]+)'))[1] AS INTEGER);

-- Normalizar estado legacy 'aprobado' -> 'confirmado' (enum actual)
UPDATE pagos SET estado = 'confirmado' WHERE estado = 'aprobado';

-- Matrícula legacy a monto estándar (200 Bs)
UPDATE pagos
SET monto = 200.00
WHERE id_detalle_programa_modulo IS NULL
  AND concepto ILIKE 'Matrícula%'
  AND monto <> 200.00;
