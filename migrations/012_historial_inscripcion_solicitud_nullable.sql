-- 012: el retiro no tiene solicitud asociada -> id_solicitud pasa a nullable
ALTER TABLE historial_inscripcion ALTER COLUMN id_solicitud DROP NOT NULL;
