"""crear tabla modalidad_tipo_programa

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'modalidad_tipo_programa',
        sa.Column('id_modalidad_academica', sa.Integer(), nullable=False),
        sa.Column('id_tipo_programa', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['id_modalidad_academica'], ['modalidades_academicas.id_modalidad_academica'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['id_tipo_programa'], ['tipos_programa.id_tipo_programa'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_modalidad_academica', 'id_tipo_programa'),
    )


def downgrade() -> None:
    op.drop_table('modalidad_tipo_programa')
