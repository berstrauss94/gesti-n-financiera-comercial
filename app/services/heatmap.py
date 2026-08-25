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
from app.models.income import DailyIncome
from app.models.expense import Salary, VariableExpense, OperatingCost
from app.models.owner_withdrawal import OwnerWithdrawal
from app.models.threshold_config import ThresholdConfig, DEFAULT_THRESHOLDS


HEATMAP_COLORS = {
    'green': '🟢',
    'yellow': '🟡',
    'orange': '🟠',
    'red': '🔴',
    'critical': '🚨',
    'neutral': '⚪',
}

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

    # 6. Build indicators
    indicators = {}

    # Salarios
    sal_amount = float(salary_total)
    sal_pct = calculate_percentage_of_income(sal_amount, gross_income)
    sal_thresholds = _get_thresholds_for_category(business_id, 'salarios')
    indicators['salarios'] = {
        'amount': sal_amount,
        'percentage': sal_pct,
        'color': calculate_heatmap_color(sal_pct, sal_thresholds),
    }

    # Retiros del dueño
    wd_amount = float(withdrawal_total)
    wd_pct = calculate_percentage_of_income(wd_amount, gross_income)
    wd_thresholds = _get_thresholds_for_category(business_id, 'retiros_dueno')
    indicators['retiros_dueno'] = {
        'amount': wd_amount,
        'percentage': wd_pct,
        'color': calculate_heatmap_color(wd_pct, wd_thresholds),
    }

    # Variable expense categories
    variable_categories = [
        'comisiones', 'mermas', 'servicios', 'insumos',
        'mantenimiento', 'impuestos_municipales', 'seguros', 'logistica',
    ]
    for cat in variable_categories:
        amount = variable_by_category.get(cat, 0.0)
        pct = calculate_percentage_of_income(amount, gross_income)
        thresholds = _get_thresholds_for_category(business_id, cat)
        indicators[cat] = {
            'amount': amount,
            'percentage': pct,
            'color': calculate_heatmap_color(pct, thresholds),
        }

    # Operating cost categories
    operating_categories = ['electricidad', 'monotributo', 'alquiler', 'contable']
    for cat in operating_categories:
        amount = operating_by_category.get(cat, 0.0)
        pct = calculate_percentage_of_income(amount, gross_income)
        thresholds = _get_thresholds_for_category(business_id, cat)
        indicators[cat] = {
            'amount': amount,
            'percentage': pct,
            'color': calculate_heatmap_color(pct, thresholds),
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
