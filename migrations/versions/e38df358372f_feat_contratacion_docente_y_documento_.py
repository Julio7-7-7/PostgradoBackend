"""feat: contratacion docente y documento contratacion, eliminar id_docente de detalle_modulo

Revision ID: e38df358372f
Revises: 7f13b31945b5
Create Date: 2026-06-27 19:43:38.060503

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e38df358372f'
down_revision: Union[str, Sequence[str], None] = '7f13b31945b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('contratacion_docente',
    sa.Column('id_contratacion', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('id_docente', sa.Integer(), nullable=False),
    sa.Column('id_detalle_modulo', sa.Integer(), nullable=False),
    sa.Column('monto', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['id_detalle_modulo'], ['detalle_programa_modulo.id_detalle_programa_modulo'], ),
    sa.ForeignKeyConstraint(['id_docente'], ['docentes.id_docente'], ),
    sa.PrimaryKeyConstraint('id_contratacion')
    )
    op.create_index(op.f('ix_contratacion_docente_id_contratacion'), 'contratacion_docente', ['id_contratacion'], unique=False)
    op.create_index('uq_contratacion_vigente', 'contratacion_docente', ['id_detalle_modulo'], unique=True, postgresql_where=sa.text("estado != 'truncado'"))
    op.create_table('documentos_contratacion',
    sa.Column('id_documento', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('id_contratacion', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=30), nullable=False),
    sa.Column('archivo_pdf', sa.String(length=500), nullable=True),
    sa.Column('fecha_subida', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('orden', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['id_contratacion'], ['contratacion_docente.id_contratacion'], ),
    sa.PrimaryKeyConstraint('id_documento')
    )
    op.create_index(op.f('ix_documentos_contratacion_id_documento'), 'documentos_contratacion', ['id_documento'], unique=False)

    # Migrar datos existentes: crear contratacion para cada detalle con id_docente asignado
    conn = op.get_bind()
    conn.execute(sa.text("""
        INSERT INTO contratacion_docente (id_docente, id_detalle_modulo, estado)
        SELECT id_docente, id_detalle_programa_modulo, 'formalizado'
        FROM detalle_programa_modulo
        WHERE id_docente IS NOT NULL
    """))

    op.drop_constraint(op.f('detalle_programa_modulo_id_docente_fkey'), 'detalle_programa_modulo', type_='foreignkey')
    op.drop_column('detalle_programa_modulo', 'id_docente')


def downgrade() -> None:
    op.add_column('detalle_programa_modulo', sa.Column('id_docente', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key(op.f('detalle_programa_modulo_id_docente_fkey'), 'detalle_programa_modulo', 'docentes', ['id_docente'], ['id_docente'])

    # Restaurar datos desde contratacion (solo formalizados)
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE detalle_programa_modulo d
        SET id_docente = c.id_docente
        FROM contratacion_docente c
        WHERE c.id_detalle_modulo = d.id_detalle_programa_modulo
        AND c.estado = 'formalizado'
    """))

    op.drop_index(op.f('ix_documentos_contratacion_id_documento'), table_name='documentos_contratacion')
    op.drop_table('documentos_contratacion')
    op.drop_index('uq_contratacion_vigente', table_name='contratacion_docente', postgresql_where=sa.text("estado != 'truncado'"))
    op.drop_index(op.f('ix_contratacion_docente_id_contratacion'), table_name='contratacion_docente')
    op.drop_table('contratacion_docente')
