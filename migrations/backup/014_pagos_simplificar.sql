-- 014: Simplificación de `pagos`.
-- La boleta vive en `transaccion_pago`. Los tres campos eliminados eran redundantes:
--   - fecha_pago            duplicaba transaccion_pago.fecha_pago (nunca diverge).
--   - observaciones         campo muerto: la UI siempre lo enviaba NULL (solo datos de prueba).
--   - id_detalle_programa_alumno  denormalizado; se obtiene vía JOIN a transaccion_pago.

ALTER TABLE pagos DROP COLUMN IF EXISTS fecha_pago;
ALTER TABLE pagos DROP COLUMN IF EXISTS observaciones;
ALTER TABLE pagos DROP COLUMN IF EXISTS id_detalle_programa_alumno;

DROP INDEX IF EXISTS ix_pagos_id_detalle_programa_alumno;
