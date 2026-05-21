"""refactor: mover es_historico de programa a programa_version

Revision ID: cbb61588dbac
Revises: da6feea8d568
Create Date: 2026-05-21 18:04:16.292861

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cbb61588dbac'
down_revision: Union[str, Sequence[str], None] = 'da6feea8d568'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('programas', 'es_historico')
    op.add_column('programas_version', sa.Column('es_historico', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.alter_column('programas_version', 'es_historico', server_default=None)


def downgrade() -> None:
    """Upgrade schema."""
    op.drop_column('programas_version', 'es_historico')
    op.add_column('programas', sa.Column('es_historico', sa.BOOLEAN(), server_default=sa.text('false'), nullable=False))
    op.alter_column('programas', 'es_historico', server_default=None)
