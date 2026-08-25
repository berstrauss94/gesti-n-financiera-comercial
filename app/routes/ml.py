"""ML Engine REST endpoints for predictions and recalibration."""
from flask import Blueprint, jsonify, request, session

from app.routes.business import require_business
from app.services.ml_engine import (
    ML_CATEGORIES,
    predict_next_period,
    recalibrate,
    get_all_trends,
)

ml_bp = Blueprint('ml', __name__)


@ml_bp.route('/prediction', methods=['GET'])
@require_business
def get_prediction():
    """Get ML prediction for a specific category.

    Query params:
        category (required): Financial category to predict

    Returns:
        Prediction with confidence interval, trend, and recalibration status.
        Returns ML_INSUFFICIENT_DATA (422) if fewer than 5 records exist.
    """
    category = request.args.get('category', '').strip()

    if not category:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'El parámetro "category" es requerido',
                'field': 'category',
            }
        }), 400

    if category not in ML_CATEGORIES:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_CATEGORY',
                'message': 'Categoría no válida',
                'field': 'category',
                'valid_categories': ML_CATEGORIES,
            }
        }), 400

    business_id = session['active_business_id']
    result = predict_next_period(business_id, category)

    if result['status'] == 'insufficient_data':
        return jsonify({
            'error': {
                'code': result['error_code'],
                'message': result['message'],
            },
            'records_found': result['records_found'],
            'records_required': result['records_required'],
        }), 422

    return jsonify({
        'prediction': result,
    }), 200


@ml_bp.route('/trends', methods=['GET'])
@require_business
def get_trends():
    """Get general trends for all categories.

    Returns a summary of trends across all financial categories
    for the active business.
    """
    business_id = session['active_business_id']
    trends = get_all_trends(business_id)

    return jsonify({
        'trends': trends,
        'categories_analyzed': len(trends),
    }), 200


@ml_bp.route('/recalibrate', methods=['POST'])
@require_business
def force_recalibration():
    """Force recalibration of thresholds for a specific category.

    Request body:
        {"category": "salarios"}

    Recalibrates non-custom thresholds based on actual data patterns.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'Datos de entrada requeridos',
            }
        }), 400

    category = data.get('category', '').strip()

    if not category:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'El campo "category" es requerido',
                'field': 'category',
            }
        }), 400

    if category not in ML_CATEGORIES:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_CATEGORY',
                'message': 'Categoría no válida',
                'field': 'category',
                'valid_categories': ML_CATEGORIES,
            }
        }), 400

    business_id = session['active_business_id']
    result = recalibrate(business_id, category)

    if result['status'] == 'error':
        return jsonify({
            'error': {
                'code': 'ML_RECALIBRATION_ERROR',
                'message': result['message'],
            }
        }), 404

    if result['status'] == 'insufficient_data':
        return jsonify({
            'error': {
                'code': 'ML_INSUFFICIENT_DATA',
                'message': result['message'],
            },
            'records_found': result.get('records_found', 0),
        }), 422

    return jsonify({
        'recalibration': result,
    }), 200
