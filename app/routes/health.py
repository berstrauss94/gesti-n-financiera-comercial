"""Health check endpoint."""
from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)


@health_bp.route('/health')
def health_check():
    """Health check for Railway deployment."""
    return jsonify({'status': 'healthy', 'service': 'gestion-financiera-comercial'}), 200
