-- Migración 016: informes_notas + certificados_notas
-- Informes de notas por tandas + certificados persistentes del alumno

CREATE TABLE IF NOT EXISTS informes_notas (
    id_informe SERIAL PRIMARY KEY,
    id_programa_version_edicion INT NOT NULL
        REFERENCES programa_version_edicion(id_programa_version_edicion),
    numero_tanda INT NOT NULL,
    fecha_emision DATE NOT NULL DEFAULT CURRENT_DATE,
    alumnos_ids JSONB NOT NULL DEFAULT '[]',
    estado VARCHAR(20) NOT NULL DEFAULT 'borrador',
    observaciones TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(id_programa_version_edicion, numero_tanda)
);

CREATE TABLE IF NOT EXISTS certificados_notas (
    id_certificado SERIAL PRIMARY KEY,
    id_alumno INT NOT NULL
        REFERENCES alumnos(id_alumno),
    id_programa_version_edicion INT NOT NULL
        REFERENCES programa_version_edicion(id_programa_version_edicion),
    id_informe INT NOT NULL
        REFERENCES informes_notas(id_informe),
    fecha_emision DATE NOT NULL DEFAULT CURRENT_DATE,
    ruta_pdf TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(id_alumno, id_programa_version_edicion)
);
