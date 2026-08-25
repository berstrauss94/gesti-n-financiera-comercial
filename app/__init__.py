"""Gestión Financiera Comercial - Application Factory."""
import os
from datetime import datetime, timezone

from flask import Flask, jsonify, redirect, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, logout_user, current_user
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# Paths that don't require session activity check
_PUBLIC_PATHS = frozenset([
    '/health',
    '/api/auth/login',
    '/api/auth/register',
    '/login',
    '/register',
    '/',
])


def create_app(config_name=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///dev.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_TIMEOUT_MINUTES'] = int(
        os.environ.get('SESSION_TIMEOUT_MINUTES', 30)
    )
    app.config['MAX_LOGIN_ATTEMPTS'] = int(
        os.environ.get('MAX_LOGIN_ATTEMPTS', 5)
    )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'frontend.login'
    CORS(app)

    # Configure Flask-Login user loader
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Handle unauthorized access: redirect for pages, 401 for API
    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith('/api/'):
            return jsonify({
                'error': {
                    'code': 'AUTH_SESSION_EXPIRED',
                    'message': 'Sesión expirada por inactividad',
                }
            }), 401
        return redirect(url_for('frontend.login'))

    # Session inactivity expiration middleware
    @app.before_request
    def check_session_expiration():
        """Check if session has expired due to inactivity.

        Skips public paths (login, register, health) and static files.
        If the user is authenticated and last_activity is older than
        SESSION_TIMEOUT_MINUTES, logout and return 401.
        Otherwise, update last_activity to now.
        """
        # Skip static files
        if request.path.startswith('/static/'):
            return None

        # Skip public endpoints
        if request.path in _PUBLIC_PATHS:
            return None

        # Only check authenticated users with session activity tracking
        if not current_user.is_authenticated:
            return None

        last_activity_str = session.get('last_activity')
        if last_activity_str is None:
            # No activity tracked yet - session is invalid, expire it
            logout_user()
            session.clear()
            return jsonify({
                'error': {
                    'code': 'AUTH_SESSION_EXPIRED',
                    'message': 'Sesión expirada por inactividad',
                }
            }), 401

        # Parse last_activity and check elapsed time
        now = datetime.now(timezone.utc)
        last_activity = datetime.fromisoformat(last_activity_str)
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)

        timeout_minutes = app.config.get('SESSION_TIMEOUT_MINUTES', 30)
        elapsed_minutes = (now - last_activity).total_seconds() / 60.0

        if elapsed_minutes > timeout_minutes:
            # Session expired
            logout_user()
            session.clear()
            return jsonify({
                'error': {
                    'code': 'AUTH_SESSION_EXPIRED',
                    'message': 'Sesión expirada por inactividad',
                }
            }), 401

        # Session is valid - update last_activity
        session['last_activity'] = now.isoformat()
        return None

    # Register blueprints
    from app.routes.health import health_bp
    app.register_blueprint(health_bp)

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    from app.routes.business import business_bp
    app.register_blueprint(business_bp, url_prefix='/api/businesses')

    from app.routes.income import income_bp
    app.register_blueprint(income_bp, url_prefix='/api/income')

    from app.routes.expenses import expenses_bp
    app.register_blueprint(expenses_bp, url_prefix='/api')

    from app.routes.heatmap import heatmap_bp
    app.register_blueprint(heatmap_bp, url_prefix='/api/heatmap')

    from app.routes.reports import reports_bp
    app.register_blueprint(reports_bp, url_prefix='/api/reports')

    from app.routes.ml import ml_bp
    app.register_blueprint(ml_bp, url_prefix='/api/ml')

    from app.routes.frontend import frontend_bp
    app.register_blueprint(frontend_bp)

    return app
