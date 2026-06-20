"""merge heads: control_documentacion + detalle_modulo

Revision ID: 2401f40d848e
Revises: dbc9e2010d71, 15dfe880ff9e
Create Date: 2026-06-20 17:13:43.243385

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2401f40d848e'
down_revision: Union[str, Sequence[str], None] = ('dbc9e2010d71', '15dfe880ff9e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
