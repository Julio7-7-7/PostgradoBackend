-- Migración 017: Agregar campo password_changed_at a usuarios
-- Permite rastrear cuándo se cambió la última vez la contraseña

ALTER TABLE usuarios ADD COLUMN password_changed_at TIMESTAMP NULL;

-- Inicializar con created_at para usuarios existentes
UPDATE usuarios SET password_changed_at = created_at WHERE password_changed_at IS NULL;

ALTER TABLE usuarios ALTER COLUMN password_changed_at SET NOT NULL;
ALTER TABLE usuarios ALTER COLUMN password_changed_at SET DEFAULT now();
