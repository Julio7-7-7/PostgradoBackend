-- 028_backups.sql
-- Módulo de backups: tabla para historial/registro de copias de seguridad.
CREATE TABLE IF NOT EXISTS public.backups (
    id_backup SERIAL PRIMARY KEY,
    nombre VARCHAR(250) NOT NULL,
    ruta TEXT NOT NULL,
    tamano_bytes INTEGER NOT NULL DEFAULT 0,
    origen VARCHAR(20) NOT NULL DEFAULT 'manual',  -- manual | auto | previo_a_restaurar
    estado VARCHAR(20) NOT NULL DEFAULT 'ok',      -- ok | error
    observacion TEXT,
    creado_por_id_usuario INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_backups_created_at ON public.backups (created_at DESC);
