"""Simplificar estados docente: activo/inactivo

Revision ID: 466b66a3cabe
Revises: 2401f40d848e
Create Date: 2026-06-20 17:13:54.990982

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '466b66a3cabe'
down_revision: Union[str, Sequence[str], None] = '2401f40d848e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate existing estados: disponible→activo, contratado→activo"""
    op.execute("UPDATE docentes SET estado = 'activo' WHERE estado IN ('disponible', 'contratado')")


def downgrade() -> None:
    """Reverse: activo→disponible (no podemos recuperar contratado)"""
    op.execute("UPDATE docentes SET estado = 'disponible' WHERE estado = 'activo'")
