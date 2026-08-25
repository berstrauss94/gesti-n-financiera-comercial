"""Heatmap REST API routes."""
from datetime import date as date_type, datetime, timedelta

from flask import Blueprint, jsonify, request, session

from app.routes.business import require_business
from app.services.heatmap import calculate_all_indicators, get_net_profit_indicator

heatmap_bp = Blueprint('heatmap', __name__)


@heatmap_bp.route('/daily', methods=['GET'])
@require_business
def get_daily_heatmap():
    """Get the full daily heatmap for all expense categories.

    Query params:
        date (required): Date in YYYY-MM-DD format.

    Returns:
        200 with all indicators and net profit for the given date.
        400 if date parameter is missing or invalid.
    """
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({
            'error': {
                'code': 'VALIDATION_MISSING_DATE',
                'message': 'El parámetro date es requerido (YYYY-MM-DD)',
            }
        }), 400

    try:
        target_date = date_type.fromisoformat(date_str)
    except (ValueError, TypeError):
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_DATE',
                'message': 'Formato de fecha inválido, use YYYY-MM-DD',
            }
        }), 400

    business_id = session['active_business_id']

    indicators = calculate_all_indicators(business_id, target_date)
    net_profit = get_net_profit_indicator(business_id, target_date)

    return jsonify({
        'heatmap': {
            **indicators,
            'net_profit': net_profit,
        }
    }), 200


@heatmap_bp.route('/summary', methods=['GET'])
@require_business
def get_heatmap_summary():
    """Get heatmap summary over a date range.

    Query params:
        from (required): Start date in YYYY-MM-DD format.
        to (required): End date in YYYY-MM-DD format.

    Returns:
        200 with daily heatmap data for each date in the range.
        400 if parameters are missing or invalid.
    """
    from_str = request.args.get('from')
    to_str = request.args.get('to')

    if not from_str or not to_str:
        return jsonify({
            'error': {
                'code': 'VALIDATION_MISSING_DATES',
                'message': 'Los parámetros from y to son requeridos (YYYY-MM-DD)',
            }
        }), 400

    try:
        from_date = date_type.fromisoformat(from_str)
        to_date = date_type.fromisoformat(to_str)
    except (ValueError, TypeError):
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_DATE',
                'message': 'Formato de fecha inválido, use YYYY-MM-DD',
            }
        }), 400

    if from_date > to_date:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_RANGE',
                'message': 'La fecha from debe ser anterior o igual a to',
            }
        }), 400

    # Limit range to 90 days to prevent expensive queries
    max_days = 90
    if (to_date - from_date).days > max_days:
        return jsonify({
            'error': {
                'code': 'VALIDATION_RANGE_TOO_LARGE',
                'message': f'El rango máximo permitido es {max_days} días',
            }
        }), 400

    business_id = session['active_business_id']

    days = []
    current_date = from_date
    while current_date <= to_date:
        indicators = calculate_all_indicators(business_id, current_date)
        net_profit = get_net_profit_indicator(business_id, current_date)
        days.append({
            **indicators,
            'net_profit': net_profit,
        })
        current_date += timedelta(days=1)

    return jsonify({
        'summary': {
            'from': from_date.isoformat(),
            'to': to_date.isoformat(),
            'total_days': len(days),
            'days': days,
        }
    }), 200
