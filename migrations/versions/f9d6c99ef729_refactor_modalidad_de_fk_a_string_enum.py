"""refactor_modalidad_de_fk_a_string_enum

Revision ID: f9d6c99ef729
Revises: 3b032e080033
Create Date: 2026-07-03 13:56:26.305544

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f9d6c99ef729'
down_revision: Union[str, Sequence[str], None] = '3b032e080033'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new string columns
    op.add_column('detalle_programa_modulo', sa.Column('modalidad', sa.String(length=50), nullable=True))
    op.add_column('programa_version_edicion', sa.Column('modalidad', sa.String(length=50), nullable=True))

    # 2. Migrate data from modalidades table (FK → string value)
    op.execute("""
        UPDATE detalle_programa_modulo AS dpm
        SET modalidad = m.nombre
        FROM modalidades AS m
        WHERE dpm.id_modalidad = m.id_modalidad
    """)
    op.execute("""
        UPDATE programa_version_edicion AS pve
        SET modalidad = LOWER(m.nombre)
        FROM modalidades AS m
        WHERE pve.id_modalidad = m.id_modalidad
    """)

    # 3. Set default for ediciones that somehow have no modalidad
    op.execute("UPDATE programa_version_edicion SET modalidad = 'presencial' WHERE modalidad IS NULL")

    # 4. Make programa_version_edicion.modalidad NOT NULL now
    op.alter_column('programa_version_edicion', 'modalidad', nullable=False)

    # 5. Drop FK constraints
    op.drop_constraint(op.f('detalle_programa_modulo_id_modalidad_fkey'), 'detalle_programa_modulo', type_='foreignkey')
    op.drop_constraint(op.f('programa_version_edicion_id_modalidad_fkey'), 'programa_version_edicion', type_='foreignkey')

    # 6. Drop old FK columns
    op.drop_column('detalle_programa_modulo', 'id_modalidad')
    op.drop_column('programa_version_edicion', 'id_modalidad')

    # 7. Drop old modalidades table + index
    op.drop_index(op.f('ix_modalidades_id_modalidad'), table_name='modalidades')
    op.drop_table('modalidades')


def downgrade() -> None:
    # Recreate modalidades table
    op.create_table('modalidades',
        sa.Column('id_modalidad', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('nombre', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False),
        sa.Column('descripcion', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
        sa.Column('estado', sa.VARCHAR(length=20), server_default=sa.text("'activo'::character varying"), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id_modalidad', name=op.f('modalidad_pkey')),
        sa.UniqueConstraint('nombre', name=op.f('uq_modalidades_nombre'),
                            postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_modalidades_id_modalidad'), 'modalidades', ['id_modalidad'], unique=False)

    # Insert the 3 modalidades back
    op.execute("""
        INSERT INTO modalidades (id_modalidad, nombre, descripcion, estado)
        VALUES
            (1, 'presencial', 'Modalidad presencial', 'activo'),
            (2, 'virtual', 'Modalidad virtual', 'activo'),
            (3, 'semipresencial', 'Modalidad semipresencial', 'activo')
    """)
    op.execute("ALTER SEQUENCE modalidad_id_modalidad_seq RESTART WITH 4")

    # Re-add FK columns
    op.add_column('programa_version_edicion', sa.Column('id_modalidad', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('detalle_programa_modulo', sa.Column('id_modalidad', sa.INTEGER(), autoincrement=False, nullable=True))

    # Migrate data back
    op.execute("""
        UPDATE programa_version_edicion AS pve
        SET id_modalidad = m.id_modalidad
        FROM modalidades AS m
        WHERE LOWER(pve.modalidad) = LOWER(m.nombre)
    """)
    op.execute("""
        UPDATE detalle_programa_modulo AS dpm
        SET id_modalidad = m.id_modalidad
        FROM modalidades AS m
        WHERE LOWER(dpm.modalidad) = LOWER(m.nombre)
    """)

    # Make program_version_edicion FK NOT NULL
    op.alter_column('programa_version_edicion', 'id_modalidad', nullable=False)

    # Recreate FK constraints
    op.create_foreign_key(op.f('programa_version_edicion_id_modalidad_fkey'),
                          'programa_version_edicion', 'modalidades',
                          ['id_modalidad'], ['id_modalidad'])
    op.create_foreign_key(op.f('detalle_programa_modulo_id_modalidad_fkey'),
                          'detalle_programa_modulo', 'modalidades',
                          ['id_modalidad'], ['id_modalidad'])

    # Drop string columns
    op.drop_column('detalle_programa_modulo', 'modalidad')
    op.drop_column('programa_version_edicion', 'modalidad')
