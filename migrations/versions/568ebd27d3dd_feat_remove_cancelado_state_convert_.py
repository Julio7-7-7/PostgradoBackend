"""feat: remove cancelado state, convert existing to reprogramado

Revision ID: 568ebd27d3dd
Revises: 880f059a5827
Create Date: 2026-06-15 11:19:26.333402

"""
from typing import Sequence, Union

from alembic import op


revision: str = '568ebd27d3dd'
down_revision: Union[str, Sequence[str], None] = '880f059a5827'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE detalle_programa_modulo SET estado = 'reprogramado' WHERE estado = 'cancelado'")


def downgrade() -> None:
    pass
