"""refactor: crear junction modalidad_requisito y limpiar requisitos

Revision ID: a1b2c3d4e5f6
Revises: c2d3e4f5a6b7
Create Date: 2026-07-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crear tabla junction modalidad_requisito
    op.create_table('modalidad_requisito',
        sa.Column('id_modalidad_academica', sa.Integer(), nullable=False),
        sa.Column('id_requisito', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['id_modalidad_academica'], ['modalidades_academicas.id_modalidad_academica'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_requisito'], ['requisitos.id_requisito'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_modalidad_academica', 'id_requisito')
    )

    # 2. Migrar datos existentes: copiar FK + obligatorio de requisitos a junction
    op.execute("""
        INSERT INTO modalidad_requisito (id_modalidad_academica, id_requisito, created_at)
        SELECT id_modalidad_academica, id_requisito, now()
        FROM requisitos
        WHERE id_modalidad_academica IS NOT NULL
    """)

    # 3. Quitar columna id_modalidad_academica de requisitos
    op.drop_constraint('requisitos_id_modalidad_academica_fkey', 'requisitos', type_='foreignkey')
    op.drop_constraint('uq_requisito_nombre_modalidad', 'requisitos', type_='unique')
    op.drop_column('requisitos', 'id_modalidad_academica')

    # 4. Quitar columna obligatorio de requisitos
    op.drop_column('requisitos', 'obligatorio')

    # 5. Agregar unique constraint global en nombre
    op.create_unique_constraint('uq_requisito_nombre', 'requisitos', ['nombre'])


def downgrade() -> None:
    # Revertir en orden inverso
    op.drop_constraint('uq_requisito_nombre', 'requisitos', type_='unique')

    # Restaurar columna obligatorio
    op.add_column('requisitos', sa.Column('obligatorio', sa.Boolean(), server_default='true', nullable=False))

    # Restaurar columna id_modalidad_academica
    op.add_column('requisitos', sa.Column('id_modalidad_academica', sa.Integer(), nullable=True))
    op.create_foreign_key('requisitos_id_modalidad_academica_fkey', 'requisitos', 'modalidades_academicas', ['id_modalidad_academica'], ['id_modalidad_academica'])

    # Restaurar unique constraint original
    op.create_unique_constraint('uq_requisito_nombre_modalidad', 'requisitos', ['nombre', 'id_modalidad_academica'])

    # Migrar datos de vuelta (tomar el primer registro de junction por cada requisito)
    op.execute("""
        UPDATE requisitos r
        SET id_modalidad_academica = mr.id_modalidad_academica,
            obligatorio = true
        FROM modalidad_requisito mr
        WHERE r.id_requisito = mr.id_requisito
    """)

    # Eliminar junction table
    op.drop_table('modalidad_requisito')
