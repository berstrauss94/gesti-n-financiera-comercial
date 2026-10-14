"""Add savings_allocations

Revision ID: a69ff10cf97e
Revises: 3014c5993740
Create Date: 2026-10-13 21:23:13.259470

Nota: migración depurada a mano. El autogenerate propuso recrear todas las
tablas (comparó contra un estado vacío). Esta migración crea SOLO la tabla
nueva savings_allocations.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a69ff10cf97e'
down_revision = '3014c5993740'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'savings_allocations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('savings_allocations')
