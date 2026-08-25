"""Health check and landing page."""
from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)


@health_bp.route('/')
def landing():
    """Landing page with API info."""
    return jsonify({
        'service': 'Gestión Financiera Comercial',
        'version': '1.0.0',
        'status': 'online',
        'endpoints': {
            'health': 'GET /health',
            'register': 'POST /api/auth/register',
            'login': 'POST /api/auth/login',
            'income': 'POST /api/income',
            'heatmap': 'GET /api/heatmap/daily?date=YYYY-MM-DD',
            'reports': 'GET /api/reports?granularity=monthly&from=&to=',
            'ml_prediction': 'GET /api/ml/prediction?category=',
        }
    }), 200


@health_bp.route('/health')
def health_check():
    """Health check for Railway deployment."""
    return jsonify({'status': 'healthy', 'service': 'gestion-financiera-comercial'}), 200
