-- Migración 021: Informes de notas por módulo y carreras
-- 1. Tabla carreras (catálogo de carreras con Educación Continua)
-- 2. detalle_programa_alumno.id_carrera (requerida si modalidad Educación Continua)
-- 3. informes_notas: tipo (parcial|final), contenido (snapshot congelado), generado_at

CREATE TABLE IF NOT EXISTS carreras (
    id_carrera SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    sigla VARCHAR(30),
    descripcion TEXT,
    estado VARCHAR(20) NOT NULL DEFAULT 'activo',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_carreras_nombre ON carreras (lower(nombre));

ALTER TABLE detalle_programa_alumno
    ADD COLUMN IF NOT EXISTS id_carrera INT
        REFERENCES carreras(id_carrera);

ALTER TABLE informes_notas
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'parcial',
    ADD COLUMN IF NOT EXISTS contenido JSONB,
    ADD COLUMN IF NOT EXISTS generado_at TIMESTAMP;

INSERT INTO carreras (nombre, sigla)
SELECT v.nombre, v.sigla
FROM (VALUES
    ('Ingeniería de Sistemas', 'IS'),
    ('Ingeniería Industrial', 'II'),
    ('Ingeniería de Alimentos', 'IA'),
    ('Ingeniería Informática', 'INF')
) AS v(nombre, sigla)
WHERE NOT EXISTS (SELECT 1 FROM carreras);