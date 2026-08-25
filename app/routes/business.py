"""Business management routes and multi-tenant decorator."""
from functools import wraps

from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user

from app import db
from app.models import Business
from app.models.threshold_config import seed_default_thresholds

business_bp = Blueprint('business', __name__)


def require_business(f):
    """Decorator that ensures user is authenticated and has an active business selected.

    Checks:
    1. User is authenticated (via login_required)
    2. Session has an active_business_id
    3. The business belongs to current_user and is active

    Returns 403 with BUSINESS_NOT_SELECTED if no valid business is selected.
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        active_business_id = session.get('active_business_id')

        if active_business_id is None:
            return jsonify({
                'error': {
                    'code': 'BUSINESS_NOT_SELECTED',
                    'message': 'Debe seleccionar un negocio activo',
                }
            }), 403

        # Verify that the business belongs to the current user and is active
        business = Business.query.filter_by(
            id=active_business_id,
            owner_id=current_user.id,
            is_active=True,
        ).first()

        if business is None:
            # Business doesn't exist, doesn't belong to user, or is inactive
            session.pop('active_business_id', None)
            return jsonify({
                'error': {
                    'code': 'BUSINESS_NOT_SELECTED',
                    'message': 'Debe seleccionar un negocio activo',
                }
            }), 403

        return f(*args, **kwargs)

    return decorated_function


@business_bp.route('', methods=['POST'])
@login_required
def create_business():
    """Create a new business for the current user.

    Request body:
        {"name": "Business Name"}

    On success, seeds default thresholds for the new business.
    """
    data = request.get_json(silent=True)
    if not data or not data.get('name', '').strip():
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'El nombre del negocio es requerido',
                'field': 'name',
            }
        }), 400

    name = data['name'].strip()

    business = Business(
        name=name,
        owner_id=current_user.id,
    )

    db.session.add(business)
    db.session.commit()

    # Seed default threshold configurations for the new business
    seed_default_thresholds(business.id)

    return jsonify({
        'business': {
            'id': business.id,
            'name': business.name,
            'owner_id': business.owner_id,
            'is_active': business.is_active,
            'created_at': business.created_at.isoformat() if business.created_at else None,
        }
    }), 201


@business_bp.route('', methods=['GET'])
@login_required
def list_businesses():
    """List all active businesses owned by the current user."""
    businesses = Business.query.filter_by(
        owner_id=current_user.id,
        is_active=True,
    ).order_by(Business.created_at.desc()).all()

    return jsonify({
        'businesses': [
            {
                'id': b.id,
                'name': b.name,
                'owner_id': b.owner_id,
                'is_active': b.is_active,
                'created_at': b.created_at.isoformat() if b.created_at else None,
            }
            for b in businesses
        ]
    }), 200


@business_bp.route('/<int:business_id>', methods=['PUT'])
@login_required
def update_business(business_id):
    """Update a business name.

    Only the owner can update their own businesses.

    Request body:
        {"name": "New Business Name"}
    """
    business = Business.query.filter_by(
        id=business_id,
        owner_id=current_user.id,
        is_active=True,
    ).first()

    if business is None:
        return jsonify({
            'error': {
                'code': 'AUTH_BUSINESS_FORBIDDEN',
                'message': 'No tiene acceso a este negocio',
            }
        }), 403

    data = request.get_json(silent=True)
    if not data or not data.get('name', '').strip():
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'El nombre del negocio es requerido',
                'field': 'name',
            }
        }), 400

    business.name = data['name'].strip()
    db.session.commit()

    return jsonify({
        'business': {
            'id': business.id,
            'name': business.name,
            'owner_id': business.owner_id,
            'is_active': business.is_active,
            'created_at': business.created_at.isoformat() if business.created_at else None,
        }
    }), 200


@business_bp.route('/<int:business_id>', methods=['DELETE'])
@login_required
def delete_business(business_id):
    """Soft-delete a business (set is_active=False).

    Only the owner can delete their own businesses.
    If the deleted business is the active one in session, remove it from session.
    """
    business = Business.query.filter_by(
        id=business_id,
        owner_id=current_user.id,
        is_active=True,
    ).first()

    if business is None:
        return jsonify({
            'error': {
                'code': 'AUTH_BUSINESS_FORBIDDEN',
                'message': 'No tiene acceso a este negocio',
            }
        }), 403

    business.is_active = False
    db.session.commit()

    # If the deleted business was the active one, remove from session
    if session.get('active_business_id') == business.id:
        session.pop('active_business_id', None)

    return jsonify({
        'message': 'Negocio eliminado exitosamente',
    }), 200


@business_bp.route('/<int:business_id>/select', methods=['POST'])
@login_required
def select_business(business_id):
    """Set a business as the active business in the session.

    Only active businesses owned by the current user can be selected.
    """
    business = Business.query.filter_by(
        id=business_id,
        owner_id=current_user.id,
        is_active=True,
    ).first()

    if business is None:
        return jsonify({
            'error': {
                'code': 'AUTH_BUSINESS_FORBIDDEN',
                'message': 'No tiene acceso a este negocio',
            }
        }), 403

    # Store the active business ID in the Flask session
    session['active_business_id'] = business.id

    return jsonify({
        'message': 'Negocio seleccionado exitosamente',
        'active_business': {
            'id': business.id,
            'name': business.name,
        }
    }), 200
