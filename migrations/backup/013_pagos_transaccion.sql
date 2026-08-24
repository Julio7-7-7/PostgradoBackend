-- 013: Transacciones de pago (boletas).
-- Una boleta física (el estudiante paga en caja y lleva el comprobante a la oficina)
-- genera UNA transacción con N filas de asignación en `pagos` (una por cuota/matrícula alcanzada).
-- La matriz sigue en totales por cuota; la transacción permite el desglose por boleta,
-- la anulación con auditoría (quién/cuándo/por qué) y el transcript de pagos del alumno.

CREATE TABLE IF NOT EXISTS transaccion_pago (
    id_transaccion           SERIAL PRIMARY KEY,
    id_detalle_programa_alumno INTEGER NOT NULL REFERENCES detalle_programa_alumno(id_detalle_programa_alumno),
    monto_total              NUMERIC(10, 2) NOT NULL,
    fecha_pago               DATE NOT NULL,
    comprobante              VARCHAR(500),
    estado                   VARCHAR(20) NOT NULL DEFAULT 'confirmado',  -- confirmado | anulado
    motivo_anulacion         TEXT,
    anulado_por_id_usuario   INTEGER REFERENCES usuarios(id_usuario),
    anulado_fecha            TIMESTAMP,
    creado_por_id_usuario    INTEGER REFERENCES usuarios(id_usuario),
    created_at               TIMESTAMP NOT NULL DEFAULT now(),
    updated_at               TIMESTAMP NOT NULL DEFAULT now()
);

-- Backfill: una transacción por fila de pago existente (conserva los totales actuales).
-- Normalización de estados legacy:
--   confirmado -> confirmado
--   pendiente  -> confirmado  (regla vigente: si se sube, sirve)
--   rechazado  -> anulado     (ya no se rechaza; se conserva como dado de baja)
ALTER TABLE transaccion_pago ADD COLUMN IF NOT EXISTS id_pago_backfill INTEGER;

INSERT INTO transaccion_pago (
    id_detalle_programa_alumno, monto_total, fecha_pago, comprobante,
    estado, motivo_anulacion, anulado_por_id_usuario, anulado_fecha,
    created_at, updated_at, id_pago_backfill
)
SELECT
    id_detalle_programa_alumno,
    monto,
    fecha_pago,
    comprobante_url,
    CASE estado
        WHEN 'rechazado' THEN 'anulado'
        ELSE 'confirmado'
    END,
    CASE estado
        WHEN 'rechazado' THEN 'Pago histórico con estado rechazado — conservado como anulado.'
        ELSE NULL
    END,
    NULL, NULL,
    created_at, updated_at,
    id_pago
FROM pagos;

-- Vínculo filas -> transacción
ALTER TABLE pagos ADD COLUMN id_transaccion INTEGER REFERENCES transaccion_pago(id_transaccion);

UPDATE pagos p
SET id_transaccion = t.id_transaccion
FROM transaccion_pago t
WHERE t.id_pago_backfill = p.id_pago;

ALTER TABLE pagos ALTER COLUMN id_transaccion SET NOT NULL;

-- Limpieza del backfill
ALTER TABLE transaccion_pago DROP COLUMN id_pago_backfill;

-- Los campos de la boleta viven ahora en transaccion_pago
ALTER TABLE pagos DROP COLUMN comprobante_url;
ALTER TABLE pagos DROP COLUMN numero_referencia;
ALTER TABLE pagos DROP COLUMN estado;

-- Índices
CREATE INDEX IF NOT EXISTS ix_pagos_id_detalle_programa_alumno ON pagos(id_detalle_programa_alumno);
CREATE INDEX IF NOT EXISTS ix_pagos_id_transaccion ON pagos(id_transaccion);
CREATE INDEX IF NOT EXISTS ix_transaccion_pago_id_dpa ON transaccion_pago(id_detalle_programa_alumno);
