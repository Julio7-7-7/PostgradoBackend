-- 025_limpiar_control_doc_cartas.sql
-- Limpieza de datos: quitar controles de documentación de "Carta de Solicitud..."
-- (requisitos 6, 7 y 8) que fueron creados espuriamente por el flujo de aprobación
-- de solicitudes (solicitudes.py::aprobar, líneas 914-937), los cuales contaminaban
-- el control_documentacion por alumno y generaban columnas de carta en la matriz
-- de documentación para TODOS los estudiantes de una modalidad.

-- Se eliminan solo los controles espurios:
--   - 172 / 173: requisito 7 (Carta de Solicitud de Reincorporación) en DPAs REGULARES
--     (es_incorporacion = false) — DPAs 11 y 16 de la edición 4.
--   - 186: requisito 7 (Reincorporación) contradictorio en el DPA 65, que es una
--     incorporación (es_incorporacion = true) y por eso conserva su carta 6 (control 185).
--
-- Se conservan los 12 controles legítimos de requisito 6 (Carta de Solicitud de
-- Incorporación) en DPAs es_incorporacion = true (51, 59, 60, 62, 63, 64, 65, 75, 76,
-- 89, 90, 94).

BEGIN;

DELETE FROM control_documentacion
WHERE id_control_documentacion IN (172, 173, 186);

COMMIT;
