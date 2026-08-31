-- 027_agregar_codigo_boleta.sql
-- Agrega el campo "código de boleta" a la tabla transaccion_pago.
-- Es el número de recibo físico que trae el estudiante (departamento de caja
-- de la facultad). Sirve de referencia de auditoría si se pierde el recibo:
-- el código permite pedir un informe o reimpresión a caja. Es obligatorio al
-- registrar el cobro; el comprobante (archivo) pasa a ser opcional.

BEGIN;

ALTER TABLE transaccion_pago
  ADD COLUMN IF NOT EXISTS codigo_boleta VARCHAR(50) NULL;

COMMIT;
