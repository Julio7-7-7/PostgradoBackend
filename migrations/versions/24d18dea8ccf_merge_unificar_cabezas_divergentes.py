"""merge: unificar cabezas divergentes

Revision ID: 24d18dea8ccf
Revises: 15dfe880ff9e, 94036ea19626
Create Date: 2026-05-28 23:08:54.683063

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '24d18dea8ccf'
down_revision: Union[str, Sequence[str], None] = ('15dfe880ff9e', '94036ea19626')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
