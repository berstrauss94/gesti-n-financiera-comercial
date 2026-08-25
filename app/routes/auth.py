"""Authentication routes."""
from datetime import datetime, timedelta, timezone

import bcrypt
from flask import Blueprint, jsonify, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import User
from app.schemas import LoginSchema, UserRegistrationSchema

auth_bp = Blueprint('auth', __name__)

# Schema instances
_registration_schema = UserRegistrationSchema()

# Mapping of Marshmallow field errors to specific error codes
_FIELD_ERROR_CODE_MAP = {
    'username': {
        'Username debe tener mínimo 8 caracteres': 'VALIDATION_USERNAME_LENGTH',
        'Username debe contener al menos una mayúscula': 'VALIDATION_USERNAME_UPPERCASE',
    },
    'email': {
        'Email inválido': 'VALIDATION_EMAIL_FORMAT',
    },
    'phone': {
        'Número de celular debe tener entre 7 y 15 dígitos': 'VALIDATION_PHONE_FORMAT',
    },
}


def _build_validation_error_response(field: str, message: str, code: str):
    """Build a standardized validation error response."""
    return jsonify({
        'error': {
            'code': code,
            'message': message,
            'field': field,
        }
    }), 400


def _get_error_code(field: str, message: str) -> str:
    """Resolve the specific error code for a field/message combination."""
    field_map = _FIELD_ERROR_CODE_MAP.get(field, {})
    return field_map.get(message, f'VALIDATION_{field.upper()}_INVALID')


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user with full validation."""
    # Parse JSON body
    json_data = request.get_json(silent=True)
    if not json_data:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_INPUT',
                'message': 'Request body must be valid JSON',
                'field': None,
            }
        }), 400

    # Validate input using Marshmallow schema
    try:
        data = _registration_schema.load(json_data)
    except ValidationError as err:
        # Return the first validation error with its specific code
        for field, messages in err.messages.items():
            message = messages[0] if isinstance(messages, list) else messages
            code = _get_error_code(field, message)
            return _build_validation_error_response(field, message, code)

    # Hash password with bcrypt
    password_hash = bcrypt.hashpw(
        data['password'].encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    # Create user
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=password_hash,
        phone=data.get('phone'),
    )

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # Determine which field caused the duplicate
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({
                'error': {
                    'code': 'DUPLICATE_USERNAME',
                    'message': 'El username ya está registrado',
                    'field': 'username',
                }
            }), 409
        return jsonify({
            'error': {
                'code': 'DUPLICATE_EMAIL',
                'message': 'El email ya está registrado',
                'field': 'email',
            }
        }), 409

    # Return success response (without password_hash)
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone': user.phone,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
        }
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user with account lockout protection.

    - Verifies account is not locked (locked_until > now)
    - Verifies password with bcrypt
    - On failure: increments failed_login_attempts, locks after 5 attempts
    - On success: resets failed_login_attempts, updates last_login, creates session
    """
    data = request.get_json()
    if not data:
        return jsonify({
            'error': {
                'code': 'AUTH_INVALID_CREDENTIALS',
                'message': 'Credenciales inválidas',
            }
        }), 401

    # Validate input schema
    schema = LoginSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify({
            'error': {
                'code': 'AUTH_INVALID_CREDENTIALS',
                'message': 'Credenciales inválidas',
            }
        }), 401

    username = data.get('username', '').strip()
    password = data.get('password', '')

    # Look up user by username
    user = User.query.filter_by(username=username).first()

    if user is None:
        # Don't reveal whether username exists
        return jsonify({
            'error': {
                'code': 'AUTH_INVALID_CREDENTIALS',
                'message': 'Credenciales inválidas',
            }
        }), 401

    # Check if account is locked
    now = datetime.now(timezone.utc)
    if user.locked_until is not None:
        locked_until = user.locked_until
        # Ensure timezone-aware comparison
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            return jsonify({
                'error': {
                    'code': 'AUTH_ACCOUNT_LOCKED',
                    'message': 'Cuenta bloqueada temporalmente',
                }
            }), 403

    # Verify password with bcrypt
    password_bytes = password.encode('utf-8')
    stored_hash = user.password_hash.encode('utf-8') if isinstance(user.password_hash, str) else user.password_hash

    if not bcrypt.checkpw(password_bytes, stored_hash):
        # Password is wrong - increment failed attempts
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

        max_attempts = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
        if user.failed_login_attempts >= max_attempts:
            # Lock the account for 15 minutes
            user.locked_until = now + timedelta(minutes=15)

        db.session.commit()

        return jsonify({
            'error': {
                'code': 'AUTH_INVALID_CREDENTIALS',
                'message': 'Credenciales inválidas',
            }
        }), 401

    # Successful login - reset counters
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = now

    db.session.commit()

    # Create session with Flask-Login
    login_user(user)

    # Store last_activity in session for inactivity tracking
    session['last_activity'] = now.isoformat()

    return jsonify({
        'message': 'Login exitoso',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        }
    }), 200


@auth_bp.route('/session', methods=['GET'])
def check_session():
    """Check current session state.

    Returns user info if session is active and valid.
    Returns AUTH_SESSION_EXPIRED if no active session.
    Note: The before_request middleware handles expiration automatically,
    so if we reach this point, the session is valid.
    """
    if not current_user.is_authenticated:
        return jsonify({
            'error': {
                'code': 'AUTH_SESSION_EXPIRED',
                'message': 'Sesión expirada por inactividad',
            }
        }), 401

    return jsonify({
        'session': {
            'active': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
            }
        }
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout user and destroy session."""
    logout_user()
    session.clear()
    return jsonify({'message': 'Logout exitoso'}), 200
