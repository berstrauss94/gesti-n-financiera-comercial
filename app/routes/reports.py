"""Reports module - generation, comparison, filtering, and export."""
import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import Blueprint, jsonify, request, session, make_response
from sqlalchemy import func, or_

from app import db
from app.models.income import DailyIncome
from app.models.expense import Salary, VariableExpense, OperatingCost
from app.models.owner_withdrawal import OwnerWithdrawal
from app.routes.business import require_business

reports_bp = Blueprint('reports', __name__)


# ---------- Helpers ----------

def _parse_date(date_str):
    """Parse a date string in YYYY-MM-DD format. Returns None on failure."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def _group_key(d, granularity):
    """Return a grouping key string for a date based on granularity."""
    if granularity == 'daily':
        return d.isoformat()
    elif granularity == 'weekly':
        # ISO week: YYYY-Www
        return f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
    elif granularity == 'monthly':
        return f"{d.year}-{d.month:02d}"
    elif granularity == 'quarterly':
        quarter = (d.month - 1) // 3 + 1
        return f"{d.year}-Q{quarter}"
    elif granularity == 'semiannual':
        half = 1 if d.month <= 6 else 2
        return f"{d.year}-H{half}"
    elif granularity == 'annual':
        return str(d.year)
    return d.isoformat()


def _query_period_data(business_id, date_from, date_to, text_filter=None):
    """Query all financial data for a period, optionally filtering by text.

    Returns a dict with:
        income: total income
        salaries: total salaries
        withdrawals: total withdrawals
        variable_expenses: total variable expenses
        operating_costs: total operating costs
        items: list of individual records (for grouping/filtering)
    """
    # Income
    income_query = DailyIncome.query.filter(
        DailyIncome.business_id == business_id,
        DailyIncome.date >= date_from,
        DailyIncome.date <= date_to,
    )
    if text_filter:
        income_query = income_query.filter(
            DailyIncome.notes.ilike(f'%{text_filter}%')
        )
    incomes = income_query.all()

    # Salaries
    salary_query = Salary.query.filter(
        Salary.business_id == business_id,
        Salary.period_start <= date_to,
        Salary.period_end >= date_from,
    )
    if text_filter:
        salary_query = salary_query.filter(
            Salary.employee_name.ilike(f'%{text_filter}%')
        )
    salaries = salary_query.all()

    # Owner withdrawals
    withdrawal_query = OwnerWithdrawal.query.filter(
        OwnerWithdrawal.business_id == business_id,
        OwnerWithdrawal.date >= date_from,
        OwnerWithdrawal.date <= date_to,
    )
    if text_filter:
        withdrawal_query = withdrawal_query.filter(
            OwnerWithdrawal.description.ilike(f'%{text_filter}%')
        )
    withdrawals = withdrawal_query.all()

    # Variable expenses
    variable_query = VariableExpense.query.filter(
        VariableExpense.business_id == business_id,
        VariableExpense.date >= date_from,
        VariableExpense.date <= date_to,
    )
    if text_filter:
        variable_query = variable_query.filter(
            or_(
                VariableExpense.category.ilike(f'%{text_filter}%'),
                VariableExpense.description.ilike(f'%{text_filter}%'),
            )
        )
    variable_expenses = variable_query.all()

    # Operating costs
    operating_query = OperatingCost.query.filter(
        OperatingCost.business_id == business_id,
        OperatingCost.month >= date_from.replace(day=1),
        OperatingCost.month <= date_to,
    )
    if text_filter:
        operating_query = operating_query.filter(
            or_(
                OperatingCost.category.ilike(f'%{text_filter}%'),
                OperatingCost.description.ilike(f'%{text_filter}%'),
            )
        )
    operating_costs = operating_query.all()

    return {
        'incomes': incomes,
        'salaries': salaries,
        'withdrawals': withdrawals,
        'variable_expenses': variable_expenses,
        'operating_costs': operating_costs,
    }


def _summarize_data(data):
    """Compute summary totals from queried data."""
    total_income = sum(float(i.amount) for i in data['incomes'])
    total_salaries = sum(float(s.amount) for s in data['salaries'])
    total_withdrawals = sum(float(w.amount) for w in data['withdrawals'])
    total_variable = sum(float(v.amount) for v in data['variable_expenses'])
    total_operating = sum(float(o.amount) for o in data['operating_costs'])
    total_expenses = total_salaries + total_withdrawals + total_variable + total_operating
    net_profit = total_income - total_expenses

    return {
        'total_income': round(total_income, 2),
        'total_salaries': round(total_salaries, 2),
        'total_withdrawals': round(total_withdrawals, 2),
        'total_variable_expenses': round(total_variable, 2),
        'total_operating_costs': round(total_operating, 2),
        'total_expenses': round(total_expenses, 2),
        'net_profit': round(net_profit, 2),
    }


def _build_grouped_report(data, granularity, date_from, date_to):
    """Build a grouped report with totals, averages, and trend data."""
    # Group incomes by granularity
    groups = {}

    for income in data['incomes']:
        key = _group_key(income.date, granularity)
        if key not in groups:
            groups[key] = {
                'period': key,
                'income': 0.0,
                'salaries': 0.0,
                'withdrawals': 0.0,
                'variable_expenses': 0.0,
                'operating_costs': 0.0,
            }
        groups[key]['income'] += float(income.amount)

    for salary in data['salaries']:
        # Use the midpoint of the salary period for grouping
        mid_date = salary.period_start + (salary.period_end - salary.period_start) / 2
        key = _group_key(mid_date, granularity)
        if key not in groups:
            groups[key] = {
                'period': key,
                'income': 0.0,
                'salaries': 0.0,
                'withdrawals': 0.0,
                'variable_expenses': 0.0,
                'operating_costs': 0.0,
            }
        groups[key]['salaries'] += float(salary.amount)

    for w in data['withdrawals']:
        key = _group_key(w.date, granularity)
        if key not in groups:
            groups[key] = {
                'period': key,
                'income': 0.0,
                'salaries': 0.0,
                'withdrawals': 0.0,
                'variable_expenses': 0.0,
                'operating_costs': 0.0,
            }
        groups[key]['withdrawals'] += float(w.amount)

    for v in data['variable_expenses']:
        key = _group_key(v.date, granularity)
        if key not in groups:
            groups[key] = {
                'period': key,
                'income': 0.0,
                'salaries': 0.0,
                'withdrawals': 0.0,
                'variable_expenses': 0.0,
                'operating_costs': 0.0,
            }
        groups[key]['variable_expenses'] += float(v.amount)

    for o in data['operating_costs']:
        key = _group_key(o.month, granularity)
        if key not in groups:
            groups[key] = {
                'period': key,
                'income': 0.0,
                'salaries': 0.0,
                'withdrawals': 0.0,
                'variable_expenses': 0.0,
                'operating_costs': 0.0,
            }
        groups[key]['operating_costs'] += float(o.amount)

    # Sort groups by period key
    sorted_groups = sorted(groups.values(), key=lambda g: g['period'])

    # Calculate net profit for each group
    for g in sorted_groups:
        g['total_expenses'] = round(
            g['salaries'] + g['withdrawals'] + g['variable_expenses'] + g['operating_costs'], 2
        )
        g['net_profit'] = round(g['income'] - g['total_expenses'], 2)
        # Round all values
        g['income'] = round(g['income'], 2)
        g['salaries'] = round(g['salaries'], 2)
        g['withdrawals'] = round(g['withdrawals'], 2)
        g['variable_expenses'] = round(g['variable_expenses'], 2)
        g['operating_costs'] = round(g['operating_costs'], 2)

    # Compute totals and averages
    summary = _summarize_data(data)
    num_periods = len(sorted_groups) if sorted_groups else 1

    averages = {
        'avg_income': round(summary['total_income'] / num_periods, 2),
        'avg_expenses': round(summary['total_expenses'] / num_periods, 2),
        'avg_net_profit': round(summary['net_profit'] / num_periods, 2),
    }

    # Trend: income direction over groups
    trend = 'stable'
    if len(sorted_groups) >= 2:
        first_income = sorted_groups[0]['income']
        last_income = sorted_groups[-1]['income']
        if last_income > first_income:
            trend = 'up'
        elif last_income < first_income:
            trend = 'down'

    return {
        'period_from': date_from.isoformat(),
        'period_to': date_to.isoformat(),
        'granularity': granularity,
        'summary': summary,
        'averages': averages,
        'trend': trend,
        'groups': sorted_groups,
    }


# ---------- Endpoints ----------

@reports_bp.route('', methods=['GET'])
@require_business
def get_report():
    """Generate report with optional granularity, date range, and text filter.

    Query params:
        granularity: daily|weekly|monthly|quarterly|semiannual|annual (default: monthly)
        from: start date (YYYY-MM-DD)
        to: end date (YYYY-MM-DD)
        filter: text filter on category/description (case-insensitive)
    """
    business_id = session.get('active_business_id')

    granularity = request.args.get('granularity', 'monthly')
    valid_granularities = ('daily', 'weekly', 'monthly', 'quarterly', 'semiannual', 'annual')
    if granularity not in valid_granularities:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': f'Granularidad inválida. Opciones: {", ".join(valid_granularities)}',
                'field': 'granularity',
            }
        }), 400

    date_from = _parse_date(request.args.get('from'))
    date_to = _parse_date(request.args.get('to'))

    if not date_from or not date_to:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'Se requieren parámetros "from" y "to" en formato YYYY-MM-DD',
                'field': 'date_range',
            }
        }), 400

    if date_from > date_to:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'La fecha "from" no puede ser posterior a "to"',
                'field': 'date_range',
            }
        }), 400

    text_filter = request.args.get('filter', '').strip() or None

    data = _query_period_data(business_id, date_from, date_to, text_filter)
    report = _build_grouped_report(data, granularity, date_from, date_to)

    if text_filter:
        report['filter_applied'] = text_filter

    return jsonify({'report': report}), 200


@reports_bp.route('/compare', methods=['GET'])
@require_business
def compare_periods():
    """Compare two periods side-by-side.

    Query params:
        period1_from, period1_to: first period date range
        period2_from, period2_to: second period date range
    """
    business_id = session.get('active_business_id')

    p1_from = _parse_date(request.args.get('period1_from'))
    p1_to = _parse_date(request.args.get('period1_to'))
    p2_from = _parse_date(request.args.get('period2_from'))
    p2_to = _parse_date(request.args.get('period2_to'))

    if not all([p1_from, p1_to, p2_from, p2_to]):
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'Se requieren period1_from, period1_to, period2_from, period2_to en formato YYYY-MM-DD',
                'field': 'date_range',
            }
        }), 400

    # Query data for both periods
    data1 = _query_period_data(business_id, p1_from, p1_to)
    data2 = _query_period_data(business_id, p2_from, p2_to)

    summary1 = _summarize_data(data1)
    summary2 = _summarize_data(data2)

    # Calculate comparison metrics
    comparison = {}
    metrics = [
        'total_income', 'total_salaries', 'total_withdrawals',
        'total_variable_expenses', 'total_operating_costs',
        'total_expenses', 'net_profit',
    ]

    for metric in metrics:
        val1 = summary1[metric]
        val2 = summary2[metric]
        absolute_diff = round(val2 - val1, 2)

        if val1 != 0:
            percentage_diff = round((absolute_diff / abs(val1)) * 100, 2)
        else:
            percentage_diff = None

        comparison[metric] = {
            'period1': val1,
            'period2': val2,
            'absolute_diff': absolute_diff,
            'percentage_diff': percentage_diff,
        }

    return jsonify({
        'comparison': {
            'period1': {'from': p1_from.isoformat(), 'to': p1_to.isoformat()},
            'period2': {'from': p2_from.isoformat(), 'to': p2_to.isoformat()},
            'metrics': comparison,
        }
    }), 200


@reports_bp.route('/export', methods=['GET'])
@require_business
def export_report():
    """Export report as PDF or CSV.

    Query params:
        format: pdf|csv
        from: start date (YYYY-MM-DD)
        to: end date (YYYY-MM-DD)
    """
    business_id = session.get('active_business_id')

    export_format = request.args.get('format', '').lower()
    if export_format not in ('pdf', 'csv'):
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'Formato inválido. Opciones: pdf, csv',
                'field': 'format',
            }
        }), 400

    date_from = _parse_date(request.args.get('from'))
    date_to = _parse_date(request.args.get('to'))

    if not date_from or not date_to:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'Se requieren parámetros "from" y "to" en formato YYYY-MM-DD',
                'field': 'date_range',
            }
        }), 400

    data = _query_period_data(business_id, date_from, date_to)
    summary = _summarize_data(data)

    if export_format == 'csv':
        return _export_csv(data, summary, date_from, date_to)
    else:
        return _export_pdf(data, summary, date_from, date_to)


def _export_csv(data, summary, date_from, date_to):
    """Generate a CSV export of the report data."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['Reporte Financiero'])
    writer.writerow([f'Período: {date_from.isoformat()} a {date_to.isoformat()}'])
    writer.writerow([])

    # Summary section
    writer.writerow(['Resumen'])
    writer.writerow(['Concepto', 'Monto'])
    writer.writerow(['Ingreso Total', summary['total_income']])
    writer.writerow(['Salarios', summary['total_salaries']])
    writer.writerow(['Retiros del Dueño', summary['total_withdrawals']])
    writer.writerow(['Gastos Variables', summary['total_variable_expenses']])
    writer.writerow(['Costos Operativos', summary['total_operating_costs']])
    writer.writerow(['Total Gastos', summary['total_expenses']])
    writer.writerow(['Ganancia Neta', summary['net_profit']])
    writer.writerow([])

    # Income details
    writer.writerow(['Ingresos Diarios'])
    writer.writerow(['Fecha', 'Monto', 'Notas'])
    for income in data['incomes']:
        writer.writerow([income.date.isoformat(), float(income.amount), income.notes or ''])
    writer.writerow([])

    # Salary details
    writer.writerow(['Salarios'])
    writer.writerow(['Empleado', 'Monto', 'Período Inicio', 'Período Fin'])
    for sal in data['salaries']:
        writer.writerow([
            sal.employee_name, float(sal.amount),
            sal.period_start.isoformat(), sal.period_end.isoformat()
        ])
    writer.writerow([])

    # Withdrawals
    writer.writerow(['Retiros del Dueño'])
    writer.writerow(['Fecha', 'Monto', 'Descripción'])
    for w in data['withdrawals']:
        writer.writerow([w.date.isoformat(), float(w.amount), w.description or ''])
    writer.writerow([])

    # Variable expenses
    writer.writerow(['Gastos Variables'])
    writer.writerow(['Fecha', 'Categoría', 'Monto', 'Descripción'])
    for v in data['variable_expenses']:
        writer.writerow([
            v.date.isoformat(), v.category, float(v.amount), v.description or ''
        ])
    writer.writerow([])

    # Operating costs
    writer.writerow(['Costos Operativos'])
    writer.writerow(['Mes', 'Categoría', 'Monto', 'Descripción'])
    for o in data['operating_costs']:
        writer.writerow([
            o.month.isoformat(), o.category, float(o.amount), o.description or ''
        ])

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = (
        f'attachment; filename=reporte_{date_from.isoformat()}_{date_to.isoformat()}.csv'
    )
    return response


def _export_pdf(data, summary, date_from, date_to):
    """Generate a PDF export of the report data using reportlab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph('Reporte Financiero', styles['Title']))
    elements.append(Paragraph(
        f'Período: {date_from.isoformat()} a {date_to.isoformat()}',
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.3 * inch))

    # Summary table
    elements.append(Paragraph('Resumen', styles['Heading2']))
    summary_data = [
        ['Concepto', 'Monto'],
        ['Ingreso Total', f'${summary["total_income"]:,.2f}'],
        ['Salarios', f'${summary["total_salaries"]:,.2f}'],
        ['Retiros del Dueño', f'${summary["total_withdrawals"]:,.2f}'],
        ['Gastos Variables', f'${summary["total_variable_expenses"]:,.2f}'],
        ['Costos Operativos', f'${summary["total_operating_costs"]:,.2f}'],
        ['Total Gastos', f'${summary["total_expenses"]:,.2f}'],
        ['Ganancia Neta', f'${summary["net_profit"]:,.2f}'],
    ]
    summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Income details
    if data['incomes']:
        elements.append(Paragraph('Ingresos Diarios', styles['Heading2']))
        income_rows = [['Fecha', 'Monto', 'Notas']]
        for income in data['incomes']:
            income_rows.append([
                income.date.isoformat(),
                f'${float(income.amount):,.2f}',
                income.notes or '',
            ])
        income_table = Table(income_rows, colWidths=[1.5 * inch, 1.5 * inch, 3 * inch])
        income_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        elements.append(income_table)
        elements.append(Spacer(1, 0.2 * inch))

    # Variable expenses
    if data['variable_expenses']:
        elements.append(Paragraph('Gastos Variables', styles['Heading2']))
        var_rows = [['Fecha', 'Categoría', 'Monto', 'Descripción']]
        for v in data['variable_expenses']:
            var_rows.append([
                v.date.isoformat(),
                v.category,
                f'${float(v.amount):,.2f}',
                v.description or '',
            ])
        var_table = Table(var_rows, colWidths=[1.2 * inch, 1.5 * inch, 1.2 * inch, 2.1 * inch])
        var_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ]))
        elements.append(var_table)
        elements.append(Spacer(1, 0.2 * inch))

    # Build PDF
    doc.build(elements)

    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = (
        f'attachment; filename=reporte_{date_from.isoformat()}_{date_to.isoformat()}.pdf'
    )
    return response
