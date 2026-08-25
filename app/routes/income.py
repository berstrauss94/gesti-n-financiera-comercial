"""Daily gross income CRUD routes."""
from flask import Blueprint, jsonify, request, session

from app import db
from app.models.income import DailyIncome
from app.routes.business import require_business
from app.schemas import IncomeSchema

income_bp = Blueprint('income', __name__)
income_schema = IncomeSchema()


@income_bp.route('', methods=['POST'])
@require_business
def create_income():
    """Register daily gross income.

    Request body:
        {"amount": 1500.50, "date": "2024-01-15", "notes": "optional note"}

    Returns 409 INCOME_DUPLICATE_DATE if income already exists for that date+business.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'Datos de entrada requeridos',
            }
        }), 400

    # Validate with Marshmallow schema
    errors = income_schema.validate(data)
    if errors:
        # Return first validation error
        first_field = next(iter(errors))
        first_message = errors[first_field][0]
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': first_message,
                'field': first_field,
            }
        }), 400

    parsed = income_schema.load(data)
    business_id = session['active_business_id']

    # Check for duplicate date+business
    existing = DailyIncome.query.filter_by(
        business_id=business_id,
        date=parsed['date'],
    ).first()

    if existing:
        return jsonify({
            'error': {
                'code': 'INCOME_DUPLICATE_DATE',
                'message': 'Ya existe un ingreso para esta fecha',
                'existing_id': existing.id,
            }
        }), 409

    income = DailyIncome(
        business_id=business_id,
        date=parsed['date'],
        amount=parsed['amount'],
        notes=parsed.get('notes'),
    )

    db.session.add(income)
    db.session.commit()

    return jsonify({
        'income': _serialize_income(income),
    }), 201


@income_bp.route('', methods=['GET'])
@require_business
def query_income():
    """Query income by specific date or date range.

    Query params:
        - date=YYYY-MM-DD: single date query
        - from=YYYY-MM-DD&to=YYYY-MM-DD: range query

    If no params, returns all income for the active business.
    """
    from datetime import date as date_type, datetime

    business_id = session['active_business_id']
    query = DailyIncome.query.filter_by(business_id=business_id)

    # Single date query
    date_param = request.args.get('date')
    if date_param:
        try:
            target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'error': {
                    'code': 'VALIDATION_INVALID_INPUT',
                    'message': 'Formato de fecha inválido. Use YYYY-MM-DD',
                    'field': 'date',
                }
            }), 400

        income = query.filter_by(date=target_date).first()
        if income is None:
            return jsonify({'income': None}), 200
        return jsonify({'income': _serialize_income(income)}), 200

    # Range query
    from_param = request.args.get('from')
    to_param = request.args.get('to')

    if from_param and to_param:
        try:
            from_date = datetime.strptime(from_param, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_param, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'error': {
                    'code': 'VALIDATION_INVALID_INPUT',
                    'message': 'Formato de fecha inválido. Use YYYY-MM-DD',
                    'field': 'from/to',
                }
            }), 400

        if from_date > to_date:
            return jsonify({
                'error': {
                    'code': 'VALIDATION_INVALID_INPUT',
                    'message': 'La fecha "from" no puede ser posterior a "to"',
                    'field': 'from',
                }
            }), 400

        incomes = query.filter(
            DailyIncome.date >= from_date,
            DailyIncome.date <= to_date,
        ).order_by(DailyIncome.date.asc()).all()

        return jsonify({
            'incomes': [_serialize_income(i) for i in incomes],
        }), 200

    # No filter — return all for this business
    incomes = query.order_by(DailyIncome.date.desc()).all()
    return jsonify({
        'incomes': [_serialize_income(i) for i in incomes],
    }), 200


@income_bp.route('/<int:income_id>', methods=['PUT'])
@require_business
def update_income(income_id):
    """Update an existing income record.

    If the updated date conflicts with another record for the same business,
    returns 409 INCOME_DUPLICATE_DATE with the existing record id
    (client can confirm overwrite).

    Request body:
        {"amount": 2000.00, "date": "2024-01-15", "notes": "updated note", "confirm_overwrite": true}
    """
    business_id = session['active_business_id']

    income = DailyIncome.query.filter_by(
        id=income_id,
        business_id=business_id,
    ).first()

    if income is None:
        return jsonify({
            'error': {
                'code': 'INCOME_NOT_FOUND',
                'message': 'Ingreso no encontrado',
            }
        }), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'Datos de entrada requeridos',
            }
        }), 400

    # Validate with Marshmallow schema (exclude extra fields like confirm_overwrite)
    schema_data = {k: v for k, v in data.items() if k in ('amount', 'date', 'notes')}
    errors = income_schema.validate(schema_data)
    if errors:
        first_field = next(iter(errors))
        first_message = errors[first_field][0]
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': first_message,
                'field': first_field,
            }
        }), 400

    parsed = income_schema.load(schema_data)

    # Check if changing to a date that already has an income record (different id)
    if parsed['date'] != income.date:
        existing = DailyIncome.query.filter_by(
            business_id=business_id,
            date=parsed['date'],
        ).first()

        if existing and existing.id != income.id:
            # If client confirms overwrite, delete the existing and update
            if data.get('confirm_overwrite'):
                db.session.delete(existing)
                db.session.flush()
            else:
                return jsonify({
                    'error': {
                        'code': 'INCOME_DUPLICATE_DATE',
                        'message': 'Ya existe un ingreso para esta fecha',
                        'existing_id': existing.id,
                    }
                }), 409

    income.amount = parsed['amount']
    income.date = parsed['date']
    income.notes = parsed.get('notes')

    db.session.commit()

    return jsonify({
        'income': _serialize_income(income),
    }), 200


def _serialize_income(income):
    """Serialize a DailyIncome instance to dict."""
    return {
        'id': income.id,
        'business_id': income.business_id,
        'date': income.date.isoformat(),
        'amount': str(income.amount),
        'notes': income.notes,
        'created_at': income.created_at.isoformat() if income.created_at else None,
    }
