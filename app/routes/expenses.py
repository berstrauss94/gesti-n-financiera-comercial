"""Expense-related routes: salaries, owner withdrawals, variable expenses, operating costs."""
from datetime import datetime

from flask import Blueprint, jsonify, request, session
from marshmallow import ValidationError

from app import db
from app.models.expense import OperatingCost, Salary, VariableExpense
from app.models.owner_withdrawal import OwnerWithdrawal
from app.routes.business import require_business
from app.schemas import (
    OperatingCostSchema,
    OwnerWithdrawalSchema,
    SalarySchema,
    VariableExpenseSchema,
    VALID_OPERATING_COST_CATEGORIES,
    VALIDATION_INVALID_CATEGORY,
)

expenses_bp = Blueprint('expenses', __name__)

# Schema instances
_salary_schema = SalarySchema()
_withdrawal_schema = OwnerWithdrawalSchema()
_variable_expense_schema = VariableExpenseSchema()
_operating_cost_schema = OperatingCostSchema()


# --- Employee Salaries ---

@expenses_bp.route('/salaries', methods=['POST'])
@require_business
def create_salary():
    """Register a new employee salary.

    Request body:
        {
            "employee_name": "string",
            "amount": number,
            "period_start": "YYYY-MM-DD",
            "period_end": "YYYY-MM-DD"
        }

    Returns 201 with created salary record.
    Returns 400 with validation errors if input is invalid.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'Datos de entrada requeridos',
            }
        }), 400

    try:
        validated = _salary_schema.load(data)
    except ValidationError as err:
        # Return first validation error
        first_field = next(iter(err.messages))
        first_message = err.messages[first_field][0]
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': first_message,
                'field': first_field,
            }
        }), 400

    active_business_id = session.get('active_business_id')

    salary = Salary(
        business_id=active_business_id,
        employee_name=validated['employee_name'],
        amount=validated['amount'],
        period_start=validated['period_start'],
        period_end=validated['period_end'],
    )

    db.session.add(salary)
    db.session.commit()

    return jsonify({
        'salary': {
            'id': salary.id,
            'business_id': salary.business_id,
            'employee_name': salary.employee_name,
            'amount': str(salary.amount),
            'period_start': salary.period_start.isoformat(),
            'period_end': salary.period_end.isoformat(),
            'created_at': salary.created_at.isoformat() if salary.created_at else None,
        }
    }), 201


@expenses_bp.route('/salaries', methods=['GET'])
@require_business
def list_salaries():
    """Query salaries, optionally filtered by period.

    Query params:
        period: date range in format "YYYY-MM-DD,YYYY-MM-DD" (start,end)
                Filters salaries whose period overlaps the given date range.

    Returns 200 with list of salary records.
    """
    active_business_id = session.get('active_business_id')

    query = Salary.query.filter_by(business_id=active_business_id)

    period = request.args.get('period')
    if period:
        # Parse period as "start_date,end_date"
        parts = period.split(',')
        if len(parts) == 2:
            try:
                filter_start = datetime.strptime(parts[0].strip(), '%Y-%m-%d').date()
                filter_end = datetime.strptime(parts[1].strip(), '%Y-%m-%d').date()
                # Find salaries that overlap with the given date range
                # Overlap condition: salary.period_start <= filter_end AND salary.period_end >= filter_start
                query = query.filter(
                    Salary.period_start <= filter_end,
                    Salary.period_end >= filter_start,
                )
            except (ValueError, TypeError):
                return jsonify({
                    'error': {
                        'code': 'VALIDATION_INVALID_INPUT',
                        'message': 'Formato de período inválido. Use: YYYY-MM-DD,YYYY-MM-DD',
                    }
                }), 400

    salaries = query.order_by(Salary.period_start.desc()).all()

    return jsonify({
        'salaries': [
            {
                'id': s.id,
                'business_id': s.business_id,
                'employee_name': s.employee_name,
                'amount': str(s.amount),
                'period_start': s.period_start.isoformat(),
                'period_end': s.period_end.isoformat(),
                'created_at': s.created_at.isoformat() if s.created_at else None,
            }
            for s in salaries
        ]
    }), 200


# --- Owner Withdrawals ---

@expenses_bp.route('/withdrawals', methods=['POST'])
@require_business
def create_withdrawal():
    """Register an owner withdrawal.

    Request body:
        {"amount": 1500.00, "date": "2024-01-15", "description": "Retiro personal"}

    Returns 201 with the created withdrawal on success.
    Returns 400 with validation errors on invalid input.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'Request body is required',
            }
        }), 400

    # Validate input with Marshmallow schema
    try:
        validated = _withdrawal_schema.load(data)
    except ValidationError as err:
        # Return first validation error
        first_field = next(iter(err.messages))
        first_message = err.messages[first_field][0]
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': first_message,
                'field': first_field,
            }
        }), 400

    business_id = session.get('active_business_id')

    withdrawal = OwnerWithdrawal(
        business_id=business_id,
        amount=validated['amount'],
        date=validated['date'],
        description=validated.get('description'),
    )

    db.session.add(withdrawal)
    db.session.commit()

    return jsonify({
        'withdrawal': {
            'id': withdrawal.id,
            'business_id': withdrawal.business_id,
            'amount': str(withdrawal.amount),
            'date': withdrawal.date.isoformat(),
            'description': withdrawal.description,
            'created_at': withdrawal.created_at.isoformat() if withdrawal.created_at else None,
        }
    }), 201


@expenses_bp.route('/withdrawals', methods=['GET'])
@require_business
def list_withdrawals():
    """Query owner withdrawals by period.

    Query params:
        from (optional): Start date filter (YYYY-MM-DD)
        to (optional): End date filter (YYYY-MM-DD)
        period (optional): Alias; if present, interpreted as "from" and "to" as a range

    Returns 200 with list of withdrawals matching the period filter.
    """
    business_id = session.get('active_business_id')

    query = OwnerWithdrawal.query.filter_by(business_id=business_id)

    # Filter by date range
    from_date = request.args.get('from')
    to_date = request.args.get('to')

    if from_date:
        try:
            from_dt = datetime.strptime(from_date, '%Y-%m-%d').date()
            query = query.filter(OwnerWithdrawal.date >= from_dt)
        except ValueError:
            return jsonify({
                'error': {
                    'code': 'VALIDATION_INVALID_INPUT',
                    'message': 'Formato de fecha inválido para "from". Use YYYY-MM-DD',
                    'field': 'from',
                }
            }), 400

    if to_date:
        try:
            to_dt = datetime.strptime(to_date, '%Y-%m-%d').date()
            query = query.filter(OwnerWithdrawal.date <= to_dt)
        except ValueError:
            return jsonify({
                'error': {
                    'code': 'VALIDATION_INVALID_INPUT',
                    'message': 'Formato de fecha inválido para "to". Use YYYY-MM-DD',
                    'field': 'to',
                }
            }), 400

    withdrawals = query.order_by(OwnerWithdrawal.date.desc()).all()

    return jsonify({
        'withdrawals': [
            {
                'id': w.id,
                'business_id': w.business_id,
                'amount': str(w.amount),
                'date': w.date.isoformat(),
                'description': w.description,
                'created_at': w.created_at.isoformat() if w.created_at else None,
            }
            for w in withdrawals
        ]
    }), 200


# --- Variable Expenses (8 categories) ---

@expenses_bp.route('/variable-expenses', methods=['POST'])
@require_business
def create_variable_expense():
    """Register a variable expense.

    Request body:
        {
            "category": "comisiones",
            "amount": 500.00,
            "date": "2024-01-15",
            "description": "Comisión vendedor"
        }

    Valid categories: comisiones, mermas, servicios, insumos,
        mantenimiento, impuestos_municipales, seguros, logistica

    Returns 201 with the created variable expense on success.
    Returns 400 with VALIDATION_INVALID_CATEGORY if category is not valid.
    Returns 400 with validation errors on other invalid input.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'Request body is required',
            }
        }), 400

    # Validate input with Marshmallow schema
    try:
        validated = _variable_expense_schema.load(data)
    except ValidationError as err:
        # Check if category validation failed
        first_field = next(iter(err.messages))
        first_message = err.messages[first_field][0]

        # Use specific error code for invalid category
        if first_field == 'category' and first_message == VALIDATION_INVALID_CATEGORY:
            return jsonify({
                'error': {
                    'code': 'VALIDATION_INVALID_CATEGORY',
                    'message': VALIDATION_INVALID_CATEGORY,
                    'field': 'category',
                }
            }), 400

        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': first_message,
                'field': first_field,
            }
        }), 400

    business_id = session.get('active_business_id')

    expense = VariableExpense(
        business_id=business_id,
        category=validated['category'],
        amount=validated['amount'],
        date=validated['date'],
        description=validated.get('description'),
    )

    db.session.add(expense)
    db.session.commit()

    return jsonify({
        'variable_expense': {
            'id': expense.id,
            'business_id': expense.business_id,
            'category': expense.category,
            'amount': str(expense.amount),
            'date': expense.date.isoformat(),
            'description': expense.description,
            'created_at': expense.created_at.isoformat() if expense.created_at else None,
        }
    }), 201


@expenses_bp.route('/variable-expenses', methods=['GET'])
@require_business
def list_variable_expenses():
    """Query variable expenses by category and/or date range.

    Query params:
        category (optional): Filter by expense category
        from (optional): Start date filter (YYYY-MM-DD)
        to (optional): End date filter (YYYY-MM-DD)

    Returns 200 with list of variable expenses matching filters.
    Returns 400 with VALIDATION_INVALID_CATEGORY if category param is invalid.
    """
    from app.schemas import VALID_VARIABLE_EXPENSE_CATEGORIES

    business_id = session.get('active_business_id')

    query = VariableExpense.query.filter_by(business_id=business_id)

    # Filter by category
    category = request.args.get('category')
    if category:
        if category not in VALID_VARIABLE_EXPENSE_CATEGORIES:
            return jsonify({
                'error': {
                    'code': 'VALIDATION_INVALID_CATEGORY',
                    'message': VALIDATION_INVALID_CATEGORY,
                    'field': 'category',
                }
            }), 400
        query = query.filter_by(category=category)

    # Filter by date range
    from_date = request.args.get('from')
    to_date = request.args.get('to')

    if from_date:
        try:
            from_dt = datetime.strptime(from_date, '%Y-%m-%d').date()
            query = query.filter(VariableExpense.date >= from_dt)
        except ValueError:
            return jsonify({
                'error': {
                    'code': 'VALIDATION_INVALID_INPUT',
                    'message': 'Formato de fecha inválido para "from". Use YYYY-MM-DD',
                    'field': 'from',
                }
            }), 400

    if to_date:
        try:
            to_dt = datetime.strptime(to_date, '%Y-%m-%d').date()
            query = query.filter(VariableExpense.date <= to_dt)
        except ValueError:
            return jsonify({
                'error': {
                    'code': 'VALIDATION_INVALID_INPUT',
                    'message': 'Formato de fecha inválido para "to". Use YYYY-MM-DD',
                    'field': 'to',
                }
            }), 400

    expenses = query.order_by(VariableExpense.date.desc()).all()

    return jsonify({
        'variable_expenses': [
            {
                'id': e.id,
                'business_id': e.business_id,
                'category': e.category,
                'amount': str(e.amount),
                'date': e.date.isoformat(),
                'description': e.description,
                'created_at': e.created_at.isoformat() if e.created_at else None,
            }
            for e in expenses
        ]
    }), 200


# --- Operating Costs ---

@expenses_bp.route('/operating-costs', methods=['POST'])
@require_business
def create_operating_cost():
    """Register an operating cost.

    Request body:
        {
            "category": "electricidad",
            "amount": 5000.00,
            "month": "2024-01-01",
            "description": "Factura enero"
        }

    Valid categories: electricidad, monotributo, mercaderia, alquiler, contable

    Returns 201 with the created operating cost on success.
    Returns 400 with VALIDATION_INVALID_CATEGORY if category is not valid.
    Returns 400 with validation errors on other invalid input.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'Request body is required',
            }
        }), 400

    # Validate input with Marshmallow schema
    try:
        validated = _operating_cost_schema.load(data)
    except ValidationError as err:
        # Check if category validation failed
        first_field = next(iter(err.messages))
        first_message = err.messages[first_field][0]

        # Use specific error code for invalid category
        if first_field == 'category' and first_message == VALIDATION_INVALID_CATEGORY:
            return jsonify({
                'error': {
                    'code': 'VALIDATION_INVALID_CATEGORY',
                    'message': VALIDATION_INVALID_CATEGORY,
                    'field': 'category',
                }
            }), 400

        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': first_message,
                'field': first_field,
            }
        }), 400

    business_id = session.get('active_business_id')

    cost = OperatingCost(
        business_id=business_id,
        category=validated['category'],
        amount=validated['amount'],
        month=validated['month'],
        description=validated.get('description'),
    )

    db.session.add(cost)
    db.session.commit()

    return jsonify({
        'operating_cost': {
            'id': cost.id,
            'business_id': cost.business_id,
            'category': cost.category,
            'amount': str(cost.amount),
            'month': cost.month.isoformat(),
            'description': cost.description,
            'created_at': cost.created_at.isoformat() if cost.created_at else None,
        }
    }), 201


@expenses_bp.route('/operating-costs', methods=['GET'])
@require_business
def list_operating_costs():
    """Query operating costs by month.

    Query params:
        month (optional): Filter by month (YYYY-MM-DD format, first day of month)

    Returns 200 with list of operating costs matching filters.
    """
    business_id = session.get('active_business_id')

    query = OperatingCost.query.filter_by(business_id=business_id)

    # Filter by month
    month_param = request.args.get('month')
    if month_param:
        try:
            month_date = datetime.strptime(month_param, '%Y-%m-%d').date()
            query = query.filter_by(month=month_date)
        except (ValueError, TypeError):
            return jsonify({
                'error': {
                    'code': 'VALIDATION_INVALID_INPUT',
                    'message': 'Formato de mes inválido. Use YYYY-MM-DD (primer día del mes)',
                    'field': 'month',
                }
            }), 400

    costs = query.order_by(OperatingCost.month.desc()).all()

    return jsonify({
        'operating_costs': [
            {
                'id': c.id,
                'business_id': c.business_id,
                'category': c.category,
                'amount': str(c.amount),
                'month': c.month.isoformat(),
                'description': c.description,
                'created_at': c.created_at.isoformat() if c.created_at else None,
            }
            for c in costs
        ]
    }), 200
