-- Migración 018: Refactor de contrataciones de docentes
-- Agrega tablas etapa_contratacion, etapa_requisito, control_documentacion_contratacion
-- y FK id_etapa_actual en contratacion_docente

-- 1. Tabla etapa_contratacion
CREATE TABLE etapa_contratacion (
    id_etapa SERIAL PRIMARY KEY,
    id_tipo_programa INTEGER NOT NULL REFERENCES tipos_programa(id_tipo_programa),
    nombre VARCHAR(200) NOT NULL,
    orden INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_etapa_contratacion_tipo_programa ON etapa_contratacion(id_tipo_programa);

-- 2. Tabla etapa_requisito
CREATE TABLE etapa_requisito (
    id_etapa INTEGER NOT NULL REFERENCES etapa_contratacion(id_etapa) ON DELETE CASCADE,
    id_requisito INTEGER NOT NULL REFERENCES requisitos(id_requisito),
    orden INTEGER NOT NULL DEFAULT 1,
    obligatorio BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id_etapa, id_requisito)
);

-- 3. FK id_etapa_actual en contratacion_docente
ALTER TABLE contratacion_docente ADD COLUMN id_etapa_actual INTEGER REFERENCES etapa_contratacion(id_etapa);

-- 4. Tabla control_documentacion_contratacion
CREATE TABLE control_documentacion_contratacion (
    id_control_doc_contratacion SERIAL PRIMARY KEY,
    id_contratacion INTEGER NOT NULL REFERENCES contratacion_docente(id_contratacion) ON DELETE CASCADE,
    id_requisito INTEGER NOT NULL REFERENCES requisitos(id_requisito),
    id_etapa INTEGER NOT NULL REFERENCES etapa_contratacion(id_etapa),
    url_documento VARCHAR(500),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    fecha_entrega DATE,
    fecha_revision DATE,
    observaciones VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_control_doc_contratacion_contratacion ON control_documentacion_contratacion(id_contratacion);
CREATE INDEX idx_control_doc_contratacion_requisito ON control_documentacion_contratacion(id_requisito);
CREATE INDEX idx_control_doc_contratacion_etapa ON control_documentacion_contratacion(id_etapa);

-- 5. Migrar datos existentes de documentos_contratacion a control_documentacion_contratacion
-- Solo si hay datos en documentos_contratacion
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM documentos_contratacion LIMIT 1) THEN
        -- Insertar datos existentes (sin vinculación a etapa, se asignará id_etapa = NULL por ahora)
        INSERT INTO control_documentacion_contratacion (
            id_contratacion, id_requisito, id_etapa, url_documento, estado, fecha_entrega, created_at, updated_at
        )
        SELECT
            dc.id_contratacion,
            r.id_requisito,
            NULL,
            dc.archivo_pdf,
            'entregado',
            CURRENT_DATE,
            dc.created_at,
            dc.updated_at
        FROM documentos_contratacion dc
        JOIN requisitos r ON LOWER(r.nombre) = LOWER(
            CASE dc.tipo
                WHEN 'solicitud_contratacion' THEN 'Solicitud de contratación'
                WHEN 'hoja_vida' THEN 'Hoja de vida'
                WHEN 'contrato' THEN 'Contrato'
                WHEN 'resolucion' THEN 'Resolución'
                WHEN 'otro' THEN 'Otro documento'
                ELSE dc.tipo
            END
        );
    END IF;
END $$;

-- 6. NOTA: La tabla documentos_contratacion NO se elimina en esta migración
-- Se eliminará después de verificar que el frontend funcione correctamente con el nuevo modelo
