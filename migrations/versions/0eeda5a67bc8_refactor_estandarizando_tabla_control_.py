"""refactor: estandarizando tabla control documentacion y detalle_programa_alumno

Revision ID: 0eeda5a67bc8
Revises: 4b3da79bba52
Create Date: 2026-04-27 22:28:01.106755

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0eeda5a67bc8'
down_revision: Union[str, Sequence[str], None] = '4b3da79bba52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('control_documentacion', sa.Column('url_documento', sa.String(length=500), nullable=True))
    op.add_column('control_documentacion', sa.Column('estado', sa.String(length=20), nullable=False, server_default='pendiente'))
    op.add_column('control_documentacion', sa.Column('fecha_revision', sa.Date(), nullable=True))
    op.drop_column('control_documentacion', 'entregado')
    op.add_column('detalle_programa_alumno', sa.Column('descuento_aplicado', sa.Float(), nullable=False, server_default='0.0'))
    op.drop_column('detalle_programa_alumno', 'descuento')

def downgrade() -> None:
    op.add_column('detalle_programa_alumno', sa.Column('descuento', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False))
    op.drop_column('detalle_programa_alumno', 'descuento_aplicado')
    op.add_column('control_documentacion', sa.Column('entregado', sa.BOOLEAN(), autoincrement=False, nullable=False, server_default='false'))
    op.drop_column('control_documentacion', 'fecha_revision')
    op.drop_column('control_documentacion', 'estado')
    op.drop_column('control_documentacion', 'url_documento')
