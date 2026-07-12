"""migrar usuario roles a tabla intermedia

Revision ID: a1b2c3d4e5f6
Revises: None
Create Date: 2026-07-12

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'usuario_roles',
        sa.Column('id_usuario', sa.Integer(), sa.ForeignKey('usuarios.id_usuario', ondelete='CASCADE'), primary_key=True),
        sa.Column('id_rol', sa.Integer(), sa.ForeignKey('roles.id_rol', ondelete='CASCADE'), primary_key=True),
        sa.Column('rol_activo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.execute("""
        INSERT INTO usuario_roles (id_usuario, id_rol, rol_activo, created_at)
        SELECT id_usuario, id_rol, true, COALESCE(created_at, NOW())
        FROM usuarios
        WHERE id_rol IS NOT NULL
    """)

    op.drop_constraint('uq_email_rol', 'usuarios', type_='unique')
    op.drop_column('usuarios', 'id_rol')


def downgrade() -> None:
    op.add_column('usuarios', sa.Column('id_rol', sa.Integer(), sa.ForeignKey('roles.id_rol'), nullable=True))

    op.execute("""
        UPDATE usuarios u
        SET id_rol = (
            SELECT ur.id_rol
            FROM usuario_roles ur
            WHERE ur.id_usuario = u.id_usuario
            AND ur.rol_activo = true
            LIMIT 1
        )
    """)

    op.execute("""
        UPDATE usuarios u
        SET id_rol = (
            SELECT ur.id_rol
            FROM usuario_roles ur
            WHERE ur.id_usuario = u.id_usuario
            LIMIT 1
        )
        WHERE u.id_rol IS NULL
    """)

    op.alter_column('usuarios', 'id_rol', nullable=False)
    op.create_unique_constraint('uq_email_rol', 'usuarios', ['email', 'id_rol'])
    op.drop_table('usuario_roles')
