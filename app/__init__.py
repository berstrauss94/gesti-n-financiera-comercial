"""Gestión Financiera Comercial - Application Factory."""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


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
    CORS(app)

    # Register blueprints
    from app.routes.health import health_bp
    app.register_blueprint(health_bp)

    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    return app
