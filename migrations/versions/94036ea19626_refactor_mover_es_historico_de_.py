"""refactor: mover es_historico de ProgramaVersion a ProgramaVersionEdicion

Revision ID: 94036ea19626
Revises: cbb61588dbac
Create Date: 2026-05-27 12:15:03.847096

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94036ea19626'
down_revision: Union[str, Sequence[str], None] = 'cbb61588dbac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('programa_version_edicion', sa.Column('es_historico', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    op.execute("""
        UPDATE programa_version_edicion
        SET es_historico = TRUE
        FROM programas_version
        WHERE programa_version_edicion.id_programa_version = programas_version.id_programa_version
          AND programas_version.es_historico = TRUE
    """)

    op.alter_column('programa_version_edicion', 'es_historico', server_default=None)
    op.drop_column('programas_version', 'es_historico')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('programas_version', sa.Column('es_historico', sa.BOOLEAN(), autoincrement=False, nullable=False, server_default=sa.text('false')))

    op.execute("""
        UPDATE programas_version
        SET es_historico = TRUE
        FROM programa_version_edicion
        WHERE programa_version_edicion.id_programa_version = programas_version.id_programa_version
          AND programa_version_edicion.es_historico = TRUE
    """)

    op.alter_column('programas_version', 'es_historico', server_default=None)
    op.drop_column('programa_version_edicion', 'es_historico')
