"""refactor: agregar estado a horarios y mejorar router

Revision ID: 6cd48da0e373
Revises: 94036ea19626
Create Date: 2026-06-10 19:12:09.998996

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6cd48da0e373'
down_revision: Union[str, Sequence[str], None] = '94036ea19626'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('horarios', sa.Column('estado', sa.String(length=20), server_default='activo', nullable=False))
    op.alter_column('horarios', 'estado', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('horarios', 'estado')
