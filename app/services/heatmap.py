"""Heatmap calculation service.

Traffic light colors:
  🟢 Green - Healthy
  🟡 Yellow - Caution
  🟠 Orange - Warning
  🔴 Red - Danger
  🚨 Critical - Emergency
  ⚪ Gray - Neutral (no data)
"""
from decimal import Decimal

from sqlalchemy import func

from app import db
from app.catalog import operating_categories as _catalog_operating
from app.catalog import variable_categories as _catalog_variable
from app.catalog import savings_categories as _catalog_savings
from app.catalog import is_inverted as _is_inverted
from app.models.income import DailyIncome
from app.models.expense import Salary, VariableExpense, OperatingCost
from app.models.owner_withdrawal import OwnerWithdrawal
from app.models.savings import SavingsAllocation
from app.models.threshold_config import ThresholdConfig, DEFAULT_THRESHOLDS


HEATMAP_COLORS = {
    'green': '🟢',
    'yellow': '🟡',
    'orange': '🟠',
    'red': '🔴',
    'critical': '🚨',
    'neutral': '⚪',
}

# Categorías del catálogo por grupo (fuente única de verdad)
_CATALOG_VARIABLE = _catalog_variable()
_CATALOG_OPERATIVO = _catalog_operating()
_CATALOG_SAVINGS = _catalog_savings()


def _active_categories_for_business(business_id):
    """Conjunto de categorías activas de un negocio = las que tienen ThresholdConfig.

    Si el negocio no tiene ninguna configurada (caso borde), se devuelve el
    catálogo completo para preservar el comportamiento histórico.
    """
    rows = ThresholdConfig.query.filter_by(business_id=business_id).all()
    active = {r.category for r in rows}
    if not active:
        # Sin configuración: mostrar todo el catálogo (compatibilidad)
        return set(_CATALOG_VARIABLE) | set(_CATALOG_OPERATIVO) | {'salarios', 'retiros_dueno'}
    return active

# Categories tracked by the heatmap
EXPENSE_CATEGORIES = [
    'salarios',
    'retiros_dueno',
    'comisiones',
    'mermas',
    'servicios',
    'insumos',
    'mantenimiento',
    'impuestos_municipales',
    'seguros',
    'logistica',
    'electricidad',
    'monotributo',
    'alquiler',
    'contable',
]


def calculate_heatmap_color(percentage, thresholds):
    """Calculate heatmap color based on percentage and threshold config.

    Args:
        percentage: The percentage value to evaluate, or None.
        thresholds: Dict with keys 'green', 'yellow', 'orange', 'red'
                   containing upper bounds for each level.

    Returns:
        Color key string: 'neutral', 'green', 'yellow', 'orange', 'red', or 'critical'.
    """
    if percentage is None:
        return 'neutral'
    if percentage <= thresholds['green']:
        return 'green'
    elif percentage <= thresholds['yellow']:
        return 'yellow'
    elif percentage <= thresholds['orange']:
        return 'orange'
    elif percentage <= thresholds['red']:
        return 'red'
    else:
        return 'critical'


def calculate_inverted_color(percentage, thresholds):
    """Color para categorías de ahorro (lógica invertida: más % es mejor).

    thresholds: dict con 'green', 'yellow', 'orange' como MÍNIMOS.
      >= green  -> green
      >= yellow -> yellow
      >= orange -> orange
      < orange  -> red
      None      -> neutral
    """
    if percentage is None:
        return 'neutral'
    if percentage >= thresholds['green']:
        return 'green'
    elif percentage >= thresholds['yellow']:
        return 'yellow'
    elif percentage >= thresholds['orange']:
        return 'orange'
    else:
        return 'red'


def calculate_percentage_of_income(expense_amount, gross_income):
    """Calculate expense as a percentage of gross income.

    Args:
        expense_amount: The expense amount (Decimal or float).
        gross_income: The gross income amount (Decimal or float).

    Returns:
        float rounded to 2 decimals, or None if income <= 0.
    """
    if gross_income is None or gross_income <= 0:
        return None
    percentage = (float(expense_amount) / float(gross_income)) * 100
    return round(percentage, 2)


def _get_thresholds_for_category(business_id, category):
    """Get threshold dict for a given business+category.

    Looks up ThresholdConfig from the database. Falls back to DEFAULT_THRESHOLDS
    if no custom config exists.

    Returns:
        dict with keys 'green', 'yellow', 'orange', 'red'.
    """
    config = ThresholdConfig.query.filter_by(
        business_id=business_id,
        category=category,
    ).first()

    if config:
        return {
            'green': float(config.green_max),
            'yellow': float(config.yellow_max),
            'orange': float(config.orange_max),
            'red': float(config.red_max),
        }

    # Fallback to defaults
    defaults = DEFAULT_THRESHOLDS.get(category)
    if defaults:
        return {
            'green': float(defaults[0]),
            'yellow': float(defaults[1]),
            'orange': float(defaults[2]),
            'red': float(defaults[3]),
        }

    # Ultimate fallback for unknown categories
    return {'green': 5.0, 'yellow': 10.0, 'orange': 15.0, 'red': 20.0}


def calculate_all_indicators(business_id, date):
    """Calculate all heatmap indicators for a given business and date.

    Queries the day's income, sums each expense type, calculates percentage
    of income, and applies the corresponding thresholds per category.

    Args:
        business_id: ID of the business.
        date: The date to calculate indicators for.

    Returns:
        dict with structure:
        {
            'date': str,
            'gross_income': float,
            'indicators': {
                '<category>': {
                    'amount': float,
                    'percentage': float | None,
                    'color': str,
                },
                ...
            }
        }
    """
    # 1. Get gross income for the day
    income_record = DailyIncome.query.filter_by(
        business_id=business_id,
        date=date,
    ).first()

    gross_income = float(income_record.amount) if income_record else 0.0

    # 2. Sum salaries that overlap this date
    salary_total = db.session.query(
        func.coalesce(func.sum(Salary.amount), 0)
    ).filter(
        Salary.business_id == business_id,
        Salary.period_start <= date,
        Salary.period_end >= date,
    ).scalar()

    # 3. Sum owner withdrawals for this date
    withdrawal_total = db.session.query(
        func.coalesce(func.sum(OwnerWithdrawal.amount), 0)
    ).filter(
        OwnerWithdrawal.business_id == business_id,
        OwnerWithdrawal.date == date,
    ).scalar()

    # 4. Sum variable expenses by category for this date
    variable_expenses = db.session.query(
        VariableExpense.category,
        func.coalesce(func.sum(VariableExpense.amount), 0),
    ).filter(
        VariableExpense.business_id == business_id,
        VariableExpense.date == date,
    ).group_by(VariableExpense.category).all()

    variable_by_category = {cat: float(total) for cat, total in variable_expenses}

    # 5. Sum operating costs for the month containing this date
    first_of_month = date.replace(day=1)
    operating_costs = db.session.query(
        OperatingCost.category,
        func.coalesce(func.sum(OperatingCost.amount), 0),
    ).filter(
        OperatingCost.business_id == business_id,
        OperatingCost.month == first_of_month,
    ).group_by(OperatingCost.category).all()

    operating_by_category = {cat: float(total) for cat, total in operating_costs}

    # 6. Determinar qué categorías mostrar.
    # Se usan las categorías ACTIVAS del negocio (las que tienen ThresholdConfig),
    # lo que respeta el perfil y los conceptos extra opt-in. Si el negocio no
    # tuviera ninguna configurada, se cae al catálogo completo (compatibilidad).
    active_categories = _active_categories_for_business(business_id)

    # 7. Build indicators
    indicators = {}

    # Salarios (si está activo)
    if 'salarios' in active_categories:
        sal_amount = float(salary_total)
        sal_pct = calculate_percentage_of_income(sal_amount, gross_income)
        sal_thresholds = _get_thresholds_for_category(business_id, 'salarios')
        indicators['salarios'] = {
            'amount': sal_amount,
            'percentage': sal_pct,
            'color': calculate_heatmap_color(sal_pct, sal_thresholds),
        }

    # Retiros del dueño (si está activo)
    if 'retiros_dueno' in active_categories:
        wd_amount = float(withdrawal_total)
        wd_pct = calculate_percentage_of_income(wd_amount, gross_income)
        wd_thresholds = _get_thresholds_for_category(business_id, 'retiros_dueno')
        indicators['retiros_dueno'] = {
            'amount': wd_amount,
            'percentage': wd_pct,
            'color': calculate_heatmap_color(wd_pct, wd_thresholds),
        }

    # Gastos variables activos
    for cat in _CATALOG_VARIABLE:
        if cat not in active_categories:
            continue
        amount = variable_by_category.get(cat, 0.0)
        pct = calculate_percentage_of_income(amount, gross_income)
        thresholds = _get_thresholds_for_category(business_id, cat)
        indicators[cat] = {
            'amount': amount,
            'percentage': pct,
            'color': calculate_heatmap_color(pct, thresholds),
        }

    # Costos operativos activos
    for cat in _CATALOG_OPERATIVO:
        if cat not in active_categories:
            continue
        amount = operating_by_category.get(cat, 0.0)
        pct = calculate_percentage_of_income(amount, gross_income)
        thresholds = _get_thresholds_for_category(business_id, cat)
        indicators[cat] = {
            'amount': amount,
            'percentage': pct,
            'color': calculate_heatmap_color(pct, thresholds),
        }

    # Ahorros activos (lógica invertida: más % del ingreso es mejor)
    savings_by_kind = {}
    for cat in _CATALOG_SAVINGS:
        if cat not in active_categories:
            continue
        s_total = db.session.query(
            func.coalesce(func.sum(SavingsAllocation.amount), 0)
        ).filter(
            SavingsAllocation.business_id == business_id,
            SavingsAllocation.kind == cat,
            SavingsAllocation.date == date,
        ).scalar()
        amount = float(s_total)
        pct = calculate_percentage_of_income(amount, gross_income)
        thresholds = _get_thresholds_for_category(business_id, cat)
        indicators[cat] = {
            'amount': amount,
            'percentage': pct,
            'color': calculate_inverted_color(pct, thresholds),
        }

    return {
        'date': date.isoformat(),
        'gross_income': gross_income,
        'indicators': indicators,
    }


def get_net_profit_indicator(business_id, date):
    """Calculate the net profit indicator for a given business and date.

    Net Profit = Income - Salaries - Withdrawals - Variable Expenses - Operating Costs

    Thresholds (inverted - higher is better):
        >= 20% -> green
        10-20% -> yellow
        5-10%  -> orange
        < 5%   -> red

    Args:
        business_id: ID of the business.
        date: The date to calculate net profit for.

    Returns:
        dict with structure:
        {
            'date': str,
            'gross_income': float,
            'total_expenses': float,
            'net_profit': float,
            'percentage': float | None,
            'color': str,
        }
    """
    # Get gross income
    income_record = DailyIncome.query.filter_by(
        business_id=business_id,
        date=date,
    ).first()

    gross_income = float(income_record.amount) if income_record else 0.0

    # Sum salaries overlapping this date
    salary_total = float(db.session.query(
        func.coalesce(func.sum(Salary.amount), 0)
    ).filter(
        Salary.business_id == business_id,
        Salary.period_start <= date,
        Salary.period_end >= date,
    ).scalar())

    # Sum withdrawals for this date
    withdrawal_total = float(db.session.query(
        func.coalesce(func.sum(OwnerWithdrawal.amount), 0)
    ).filter(
        OwnerWithdrawal.business_id == business_id,
        OwnerWithdrawal.date == date,
    ).scalar())

    # Sum all variable expenses for this date
    variable_total = float(db.session.query(
        func.coalesce(func.sum(VariableExpense.amount), 0)
    ).filter(
        VariableExpense.business_id == business_id,
        VariableExpense.date == date,
    ).scalar())

    # Sum operating costs for the month
    first_of_month = date.replace(day=1)
    operating_total = float(db.session.query(
        func.coalesce(func.sum(OperatingCost.amount), 0)
    ).filter(
        OperatingCost.business_id == business_id,
        OperatingCost.month == first_of_month,
    ).scalar())

    # Calculate net profit
    total_expenses = salary_total + withdrawal_total + variable_total + operating_total
    net_profit = gross_income - total_expenses

    # Calculate percentage
    if gross_income <= 0:
        percentage = None
    else:
        percentage = round((net_profit / gross_income) * 100, 2)

    # Apply net profit thresholds (inverted: higher is better)
    if percentage is None:
        color = 'neutral'
    elif percentage >= 20:
        color = 'green'
    elif percentage >= 10:
        color = 'yellow'
    elif percentage >= 5:
        color = 'orange'
    else:
        color = 'red'

    return {
        'date': date.isoformat(),
        'gross_income': gross_income,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'percentage': percentage,
        'color': color,
    }
