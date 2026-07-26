"""Drop tipo and observaciones from notas

Revision ID: d4e5f6a7b8c9
"""
from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("notas", "tipo")
    op.drop_column("notas", "observaciones")


def downgrade():
    op.add_column("notas", sa.Column("tipo", sa.String(50), nullable=False, server_default="final"))
    op.add_column("notas", sa.Column("observaciones", sa.Text(), nullable=True))
