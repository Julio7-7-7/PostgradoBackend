"""merge: unificar cabezas divergentes 2

Revision ID: d91cc147dd5d
Revises: 24d18dea8ccf, dbc9e2010d71
Create Date: 2026-06-20 12:42:57.532077

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd91cc147dd5d'
down_revision: Union[str, Sequence[str], None] = ('24d18dea8ccf', 'dbc9e2010d71')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
