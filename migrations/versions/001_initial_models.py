"""Initial models - all tables for Gestión Financiera Comercial.

Revision ID: 001_initial
Revises: None
Create Date: 2024-01-01 00:00:00.000000

Tables created:
- users (with failed_login_attempts, locked_until)
- businesses
- daily_incomes
- expenses
- salaries
- variable_expenses
- operating_costs
- owner_withdrawals
- threshold_configs
- ml_predictions
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # === Users table ===
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(80), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('failed_login_attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('username', name='uq_users_username'),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )

    # === Businesses table ===
    op.create_table(
        'businesses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_businesses_owner_id', 'businesses', ['owner_id'])

    # === Daily Incomes table ===
    op.create_table(
        'daily_incomes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('business_id', sa.Integer(), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('business_id', 'date', name='uq_business_date'),
    )
    op.create_index('ix_daily_incomes_business_id', 'daily_incomes', ['business_id'])
    op.create_index('ix_daily_incomes_date', 'daily_incomes', ['date'])

    # === Expenses table (base) ===
    op.create_table(
        'expenses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('business_id', sa.Integer(), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('subcategory', sa.String(50), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_expenses_business_id', 'expenses', ['business_id'])
    op.create_index('ix_expenses_category', 'expenses', ['category'])
    op.create_index('ix_expenses_date', 'expenses', ['date'])

    # === Salaries table ===
    op.create_table(
        'salaries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('business_id', sa.Integer(), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('employee_name', sa.String(200), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_salaries_business_id', 'salaries', ['business_id'])
    op.create_index('ix_salaries_period', 'salaries', ['period_start', 'period_end'])

    # === Variable Expenses table ===
    op.create_table(
        'variable_expenses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('business_id', sa.Integer(), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_variable_expenses_business_id', 'variable_expenses', ['business_id'])
    op.create_index('ix_variable_expenses_category', 'variable_expenses', ['category'])
    op.create_index('ix_variable_expenses_date', 'variable_expenses', ['date'])

    # === Operating Costs table ===
    op.create_table(
        'operating_costs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('business_id', sa.Integer(), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_operating_costs_business_id', 'operating_costs', ['business_id'])
    op.create_index('ix_operating_costs_category', 'operating_costs', ['category'])
    op.create_index('ix_operating_costs_month', 'operating_costs', ['month'])

    # === Owner Withdrawals table ===
    op.create_table(
        'owner_withdrawals',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('business_id', sa.Integer(), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_owner_withdrawals_business_id', 'owner_withdrawals', ['business_id'])
    op.create_index('ix_owner_withdrawals_date', 'owner_withdrawals', ['date'])

    # === Threshold Configs table ===
    op.create_table(
        'threshold_configs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('business_id', sa.Integer(), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('green_max', sa.Numeric(5, 2), nullable=False),
        sa.Column('yellow_max', sa.Numeric(5, 2), nullable=False),
        sa.Column('orange_max', sa.Numeric(5, 2), nullable=False),
        sa.Column('red_max', sa.Numeric(5, 2), nullable=False),
        sa.Column('is_custom', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('business_id', 'category', name='uq_business_category_threshold'),
    )
    op.create_index('ix_threshold_configs_business_id', 'threshold_configs', ['business_id'])

    # === ML Predictions table ===
    op.create_table(
        'ml_predictions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('business_id', sa.Integer(), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('predicted_value', sa.Numeric(12, 2), nullable=False),
        sa.Column('confidence_lower', sa.Numeric(12, 2), nullable=False),
        sa.Column('confidence_upper', sa.Numeric(12, 2), nullable=False),
        sa.Column('prediction_date', sa.Date(), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=False),
        sa.Column('recalibrated', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_ml_predictions_business_id', 'ml_predictions', ['business_id'])
    op.create_index('ix_ml_predictions_category', 'ml_predictions', ['category'])
    op.create_index('ix_ml_predictions_target_date', 'ml_predictions', ['target_date'])


def downgrade():
    op.drop_table('ml_predictions')
    op.drop_table('threshold_configs')
    op.drop_table('owner_withdrawals')
    op.drop_table('operating_costs')
    op.drop_table('variable_expenses')
    op.drop_table('salaries')
    op.drop_table('expenses')
    op.drop_table('daily_incomes')
    op.drop_table('businesses')
    op.drop_table('users')
