"""Rutas de ahorro (emergencia/inversión) y agente de recomendación de umbrales.

Prefijo: /api/savings
"""
from flask import Blueprint, jsonify, request, session
from marshmallow import ValidationError

from app import db
from app.catalog import (
    CATEGORIES,
    RECOMMENDED_THRESHOLDS,
    is_inverted,
    recommended_thresholds as get_recommended,
)
from app.models.savings import SavingsAllocation, VALID_SAVINGS_KINDS
from app.models.threshold_config import ThresholdConfig
from app.routes.business import require_business

savings_bp = Blueprint('savings', __name__)


# --- CRUD de aportes de ahorro ---

@savings_bp.route('', methods=['POST'])
@require_business
def create_savings():
    """Registrar un aporte a ahorro (emergencia o inversión).

    Body: {"kind": "emergencia|inversion", "amount": 5000, "date": "2026-10-05", "description": "..."}
    """
    business_id = session.get('active_business_id')
    data = request.get_json(silent=True) or {}

    kind = (data.get('kind') or '').strip()
    if kind not in VALID_SAVINGS_KINDS:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': f'Tipo de ahorro inválido. Opciones: {", ".join(VALID_SAVINGS_KINDS)}',
                'field': 'kind',
            }
        }), 400

    amount = data.get('amount')
    date_str = data.get('date')
    if not amount or not date_str:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'amount y date son requeridos',
            }
        }), 400

    from datetime import datetime
    try:
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'Formato de fecha inválido. Use YYYY-MM-DD',
                'field': 'date',
            }
        }), 400

    record = SavingsAllocation(
        business_id=business_id,
        kind=kind,
        amount=amount,
        date=parsed_date,
        description=data.get('description'),
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({
        'savings': {
            'id': record.id,
            'kind': record.kind,
            'amount': str(record.amount),
            'date': record.date.isoformat(),
            'description': record.description,
        }
    }), 201


@savings_bp.route('', methods=['GET'])
@require_business
def list_savings():
    """Listar aportes de ahorro del negocio, con filtro opcional por kind."""
    business_id = session.get('active_business_id')
    query = SavingsAllocation.query.filter_by(business_id=business_id)

    kind = request.args.get('kind')
    if kind:
        if kind not in VALID_SAVINGS_KINDS:
            return jsonify({
                'error': {
                    'code': 'VALIDATION_INVALID_INPUT',
                    'message': 'Tipo de ahorro inválido',
                }
            }), 400
        query = query.filter_by(kind=kind)

    records = query.order_by(SavingsAllocation.date.desc()).all()
    return jsonify({
        'savings': [
            {
                'id': r.id,
                'kind': r.kind,
                'amount': str(r.amount),
                'date': r.date.isoformat(),
                'description': r.description,
            }
            for r in records
        ]
    }), 200


# --- Agente inteligente: recomendación de umbrales ---

@savings_bp.route('/recommend', methods=['GET'])
@require_business
def get_recommendations():
    """Devuelve los umbrales recomendados para todas las categorías del negocio,
    junto con los umbrales actuales, para que el usuario compare y decida.

    Fuentes de los valores recomendados:
    - Regla 50/30/20 (Elizabeth Warren, Investopedia, Ramsey Solutions)
    - Vivienda ≤25-30% del ingreso (SoFi, Financer)
    - Fondo de emergencia 3-6 meses de gastos (Vanguard, Investopedia)
    """
    business_id = session.get('active_business_id')

    configs = ThresholdConfig.query.filter_by(business_id=business_id).all()
    result = []
    for c in configs:
        rec = get_recommended(c.category)
        entry = {
            'category': c.category,
            'label': CATEGORIES.get(c.category, {}).get('label', c.category),
            'inverted': is_inverted(c.category),
            'current': {
                'green': float(c.green_max),
                'yellow': float(c.yellow_max),
                'orange': float(c.orange_max),
                'red': float(c.red_max),
            },
            'recommended': None,
            'has_recommendation': rec is not None,
        }
        if rec:
            entry['recommended'] = {
                'green': float(rec[0]),
                'yellow': float(rec[1]),
                'orange': float(rec[2]),
                'red': float(rec[3]),
            }
        result.append(entry)

    return jsonify({
        'recommendations': result,
        'sources': [
            'Regla 50/30/20 (Elizabeth Warren / Investopedia)',
            'Vivienda ≤25-30% del ingreso (Ramsey / SoFi)',
            'Fondo de emergencia 3-6 meses (Vanguard / Investopedia)',
        ],
    }), 200


@savings_bp.route('/recommend/apply', methods=['POST'])
@require_business
def apply_recommendations():
    """Aplica los umbrales recomendados a todas las categorías del negocio
    que tengan recomendación y NO sean custom (is_custom=False).

    Body opcional: {"categories": ["alquiler", "emergencia"]}
      Si no se envía, aplica a todas las que tengan recomendación.
    """
    from decimal import Decimal

    business_id = session.get('active_business_id')
    data = request.get_json(silent=True) or {}
    target_cats = data.get('categories')  # lista opcional

    configs = ThresholdConfig.query.filter_by(business_id=business_id).all()
    applied = []
    skipped = []

    for c in configs:
        if target_cats and c.category not in target_cats:
            continue
        rec = get_recommended(c.category)
        if rec is None:
            continue
        if c.is_custom:
            skipped.append({'category': c.category, 'reason': 'custom'})
            continue

        c.green_max = rec[0]
        c.yellow_max = rec[1]
        c.orange_max = rec[2]
        c.red_max = rec[3]
        applied.append(c.category)

    db.session.commit()

    return jsonify({
        'message': f'Umbrales recomendados aplicados a {len(applied)} categorías',
        'applied': applied,
        'skipped': skipped,
    }), 200


# --- Edición manual de umbrales ---

@savings_bp.route('/thresholds', methods=['GET'])
@require_business
def list_thresholds():
    """Lista todos los umbrales configurados del negocio activo."""
    business_id = session.get('active_business_id')
    configs = ThresholdConfig.query.filter_by(business_id=business_id).all()
    return jsonify({
        'thresholds': [
            {
                'id': c.id,
                'category': c.category,
                'label': CATEGORIES.get(c.category, {}).get('label', c.category),
                'inverted': is_inverted(c.category),
                'green_max': float(c.green_max),
                'yellow_max': float(c.yellow_max),
                'orange_max': float(c.orange_max),
                'red_max': float(c.red_max),
                'is_custom': c.is_custom,
            }
            for c in configs
        ]
    }), 200


@savings_bp.route('/thresholds/<category>', methods=['PUT'])
@require_business
def update_threshold(category):
    """Editar los umbrales de una categoría del negocio activo.

    Body: {"green_max": 20, "yellow_max": 25, "orange_max": 30, "red_max": 35}
    Los marca como is_custom=True (no se sobreescriben al recalibrar/recomendar).
    """
    business_id = session.get('active_business_id')
    config = ThresholdConfig.query.filter_by(
        business_id=business_id, category=category
    ).first()
    if config is None:
        return jsonify({'error': 'Categoría no encontrada en este negocio'}), 404

    data = request.get_json(silent=True) or {}
    required = ['green_max', 'yellow_max', 'orange_max', 'red_max']
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': f'Campos requeridos: {", ".join(missing)}',
            }
        }), 400

    from decimal import Decimal
    config.green_max = Decimal(str(data['green_max']))
    config.yellow_max = Decimal(str(data['yellow_max']))
    config.orange_max = Decimal(str(data['orange_max']))
    config.red_max = Decimal(str(data['red_max']))
    config.is_custom = True

    db.session.commit()

    return jsonify({
        'threshold': {
            'category': config.category,
            'green_max': float(config.green_max),
            'yellow_max': float(config.yellow_max),
            'orange_max': float(config.orange_max),
            'red_max': float(config.red_max),
            'is_custom': config.is_custom,
        }
    }), 200
