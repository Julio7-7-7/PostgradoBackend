"""feat: reemplazar gestion por semestre y anio

Revision ID: 29ed0d4713b2
Revises: f9d6c99ef729
Create Date: 2026-07-07 11:07:58.670297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29ed0d4713b2'
down_revision: Union[str, Sequence[str], None] = 'f9d6c99ef729'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('programa_version_edicion', sa.Column('semestre', sa.Integer(), nullable=True))
    op.add_column('programa_version_edicion', sa.Column('anio', sa.Integer(), nullable=True))

    op.execute("""
        UPDATE programa_version_edicion
        SET semestre = CAST(SPLIT_PART(gestion, '-', 1) AS INTEGER),
            anio = CAST(SPLIT_PART(gestion, '-', 2) AS INTEGER)
        WHERE gestion IS NOT NULL
    """)

    op.alter_column('programa_version_edicion', 'semestre', nullable=False)
    op.alter_column('programa_version_edicion', 'anio', nullable=False)
    op.drop_column('programa_version_edicion', 'gestion')


def downgrade() -> None:
    op.add_column('programa_version_edicion', sa.Column('gestion', sa.VARCHAR(), autoincrement=False, nullable=True))

    op.execute("""
        UPDATE programa_version_edicion
        SET gestion = semestre || '-' || anio
        WHERE semestre IS NOT NULL AND anio IS NOT NULL
    """)

    op.alter_column('programa_version_edicion', 'gestion', nullable=False)
    op.drop_column('programa_version_edicion', 'anio')
    op.drop_column('programa_version_edicion', 'semestre')
