"""Add enterprise modules

Revision ID: 6d0fd66a050c
Revises: 001_initial
Create Date: 2026-10-13 17:32:01.096476

Nota: Esta migración se limita a CREAR las tablas de los módulos Enterprise.
Se eliminaron a mano las operaciones espurias que el autogenerate propuso sobre
tablas preexistentes (drop_index / alter_column en incomes, expenses, salaries,
users, etc.), ya que esos índices y constraints los define la migración inicial
001 y eliminarlos rompería la retrocompatibilidad del esquema base.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d0fd66a050c'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'bank_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('bank_name', sa.String(length=100), nullable=False),
        sa.Column('account_number', sa.String(length=50), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'custom_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('target_model', sa.String(length=50), nullable=False),
        sa.Column('field_name', sa.String(length=50), nullable=False),
        sa.Column('field_label', sa.String(length=100), nullable=False),
        sa.Column('field_type', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'digital_signatures',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('document_title', sa.String(length=150), nullable=False),
        sa.Column('signer_email', sa.String(length=120), nullable=False),
        sa.Column('signature_hash', sa.String(length=256), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('signed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'document_ocrs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('raw_ocr_json', sa.JSON(), nullable=True),
        sa.Column('extracted_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('extracted_vendor', sa.String(length=100), nullable=True),
        sa.Column('extracted_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'helpdesk_tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=200), nullable=False),
        sa.Column('priority', sa.String(length=10), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('sla_deadline', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(length=50), nullable=True),
        sa.Column('barcode', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('cost_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('sale_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('stock_quantity', sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_products_barcode'), ['barcode'], unique=False)
        batch_op.create_index(batch_op.f('ix_products_sku'), ['sku'], unique=False)

    op.create_table(
        'bank_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('fitid', sa.String(length=100), nullable=True),
        sa.Column('reconciled', sa.Boolean(), nullable=True),
        sa.Column('reconciled_expense_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['bank_accounts.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fitid'),
    )
    op.create_table(
        'custom_field_values',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('field_id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('value_json', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['field_id'], ['custom_fields.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'production_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('quality_check_passed', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('production_orders')
    op.drop_table('custom_field_values')
    op.drop_table('bank_transactions')
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_products_sku'))
        batch_op.drop_index(batch_op.f('ix_products_barcode'))
    op.drop_table('products')
    op.drop_table('helpdesk_tickets')
    op.drop_table('document_ocrs')
    op.drop_table('digital_signatures')
    op.drop_table('custom_fields')
    op.drop_table('bank_accounts')
