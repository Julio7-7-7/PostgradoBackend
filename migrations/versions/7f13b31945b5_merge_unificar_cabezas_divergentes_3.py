"""merge: unificar cabezas divergentes 3

Revision ID: 7f13b31945b5
Revises: 466b66a3cabe, d91cc147dd5d
Create Date: 2026-06-27 19:43:28.791562

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f13b31945b5'
down_revision: Union[str, Sequence[str], None] = ('466b66a3cabe', 'd91cc147dd5d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
