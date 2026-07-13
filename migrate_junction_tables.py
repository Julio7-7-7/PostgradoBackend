"""
Migración: Agregar junction tables + modificar FK nullable
Ejecutar: cd PostgradoBackend && ./venv/bin/python migrate_junction_tables.py
"""
import sys
sys.path.insert(0, ".")

from database import engine
from sqlalchemy import text

def migrate():
    with engine.begin() as conn:
        # 1. Crear tabla modalidad_tipo_descuento
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS modalidad_tipo_descuento (
                id_modalidad_academica INTEGER NOT NULL
                    REFERENCES modalidades_academicas(id_modalidad_academica) ON DELETE CASCADE,
                id_tipo_descuento INTEGER NOT NULL
                    REFERENCES tipos_descuento(id_tipo_descuento) ON DELETE CASCADE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                PRIMARY KEY (id_modalidad_academica, id_tipo_descuento)
            )
        """))
        print("  OK tabla modalidad_tipo_descuento")

        # 2. Crear tabla tipo_descuento_requisito
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tipo_descuento_requisito (
                id_tipo_descuento INTEGER NOT NULL
                    REFERENCES tipos_descuento(id_tipo_descuento) ON DELETE CASCADE,
                id_requisito INTEGER NOT NULL
                    REFERENCES requisitos(id_requisito) ON DELETE CASCADE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                PRIMARY KEY (id_tipo_descuento, id_requisito)
            )
        """))
        print("  OK tabla tipo_descuento_requisito")

        # 3. Hacer id_modalidad_academica nullable en requisitos
        conn.execute(text("""
            ALTER TABLE requisitos
            ALTER COLUMN id_modalidad_academica DROP NOT NULL
        """))
        print("  OK requisitos.id_modalidad_academica ahora es nullable")

        # 4. Migrar datos existentes de tipos_descuento.id_requisito_extra
        #    a la nueva junction table tipo_descuento_requisito
        conn.execute(text("""
            INSERT INTO tipo_descuento_requisito (id_tipo_descuento, id_requisito)
            SELECT id_tipo_descuento, id_requisito_extra
            FROM tipos_descuento
            WHERE id_requisito_extra IS NOT NULL
            ON CONFLICT DO NOTHING
        """))
        print("  OK datos migrados a tipo_descuento_requisito")

        # 5. Eliminar columnas obsoletas de tipos_descuento
        conn.execute(text("ALTER TABLE tipos_descuento DROP COLUMN IF EXISTS id_requisito_extra"))
        conn.execute(text("ALTER TABLE tipos_descuento DROP COLUMN IF EXISTS requiere_documento"))
        print("  OK columnas id_requisito_extra y requiere_documento eliminadas")

    print("\nMigracion completada.")


if __name__ == "__main__":
    print("Ejecutando migracion...")
    migrate()
