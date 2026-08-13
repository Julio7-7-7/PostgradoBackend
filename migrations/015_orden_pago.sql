-- 015: Órdenes de pago.
-- Nueva regla de negocio: TODO pago nace de una orden emitida por la oficina.
-- La oficina emite una orden (impresa) que cubre la matrícula completa + N cuotas
-- íntegras y contiguas desde la primera pendiente (descuento/beca del motor financiero).
-- El alumno la lleva a caja y, al volver con la boleta, se registra el cobro enlazado
-- a la orden con la fecha real de pago (editable, puede diferir de hoy).
-- `items` es un snapshot JSONB congelado a la emisión: si mañana cambia el descuento
-- o se pierde la beca, la orden emitida no se altera.

CREATE TABLE IF NOT EXISTS orden_pago (
    id_orden_pago              SERIAL PRIMARY KEY,
    numero                     VARCHAR(20) NOT NULL UNIQUE,
    id_detalle_programa_alumno INTEGER NOT NULL REFERENCES detalle_programa_alumno(id_detalle_programa_alumno),
    fecha_emision              DATE NOT NULL DEFAULT CURRENT_DATE,
    monto_total                NUMERIC(10, 2) NOT NULL,
    items                      JSONB NOT NULL DEFAULT '[]',
    estado                     VARCHAR(20) NOT NULL DEFAULT 'emitida',  -- emitida | pagada | anulada
    motivo_anulacion           TEXT,
    anulado_por_id_usuario     INTEGER REFERENCES usuarios(id_usuario),
    anulado_fecha              TIMESTAMP,
    creado_por_id_usuario      INTEGER REFERENCES usuarios(id_usuario),
    created_at                 TIMESTAMP NOT NULL DEFAULT now(),
    updated_at                 TIMESTAMP NOT NULL DEFAULT now()
);

-- Vínculo orden -> transacción (1 orden cobrada = 1 transacción confirmada).
-- Nullable: las transacciones legacy de 013 no tienen orden asociada.
ALTER TABLE transaccion_pago ADD COLUMN IF NOT EXISTS id_orden_pago INTEGER REFERENCES orden_pago(id_orden_pago);

-- Índices
CREATE INDEX IF NOT EXISTS ix_orden_pago_id_dpa ON orden_pago(id_detalle_programa_alumno);
CREATE INDEX IF NOT EXISTS ix_orden_pago_estado ON orden_pago(estado);
CREATE INDEX IF NOT EXISTS ix_transaccion_pago_id_orden_pago ON transaccion_pago(id_orden_pago);
