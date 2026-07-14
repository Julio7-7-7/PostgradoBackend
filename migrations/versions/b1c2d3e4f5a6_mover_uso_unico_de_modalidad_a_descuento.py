"""mover uso_unico de modalidades_academicas a tipos_descuento

Revision ID: b1c2d3e4f5a6
Revises: 6cde3a8177e7, a1b2c3d4e5f6
Create Date: 2026-07-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = ('6cde3a8177e7', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregar uso_unico a tipos_descuento
    op.add_column('tipos_descuento', sa.Column('uso_unico', sa.Boolean(), nullable=False, server_default='false'))

    # Migrar datos: Beca 50% tiene uso_unico=True
    op.execute("""
        UPDATE tipos_descuento
        SET uso_unico = true
        WHERE nombre = 'Beca 50%'
    """)

    # Quitar uso_unico de modalidades_academicas
    op.drop_column('modalidades_academicas', 'uso_unico')


def downgrade() -> None:
    # Restaurar uso_unico en modalidades_academicas
    op.add_column('modalidades_academicas', sa.Column('uso_unico', sa.Boolean(), nullable=False, server_default='false'))

    # Migrar datos de vuelta
    op.execute("""
        UPDATE modalidades_academicas
        SET uso_unico = true
        WHERE id_modalidad_academica IN (
            SELECT mtd.id_modalidad_academica
            FROM modalidad_tipo_descuento mtd
            JOIN tipos_descuento td ON td.id_tipo_descuento = mtd.id_tipo_descuento
            WHERE td.uso_unico = true
        )
    """)

    # Quitar uso_unico de tipos_descuento
    op.drop_column('tipos_descuento', 'uso_unico')
