"""Add business_type to businesses

Revision ID: 3014c5993740
Revises: 6d0fd66a050c
Create Date: 2026-10-13 18:39:53.650380

Nota: migración depurada a mano para añadir SOLO la columna business_type.
Se eliminaron las operaciones espurias que el autogenerate propuso sobre
índices y constraints de tablas preexistentes (habrían roto la retrocompat).
Se usa server_default='comercio' para que las filas existentes queden con el
perfil por defecto sin violar la restricción NOT NULL.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3014c5993740'
down_revision = '6d0fd66a050c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'business_type',
                sa.String(length=30),
                nullable=False,
                server_default='comercio',
            )
        )


def downgrade():
    with op.batch_alter_table('businesses', schema=None) as batch_op:
        batch_op.drop_column('business_type')
