"""Tests for login with lockout and logout functionality."""
from datetime import datetime, timedelta, timezone

import bcrypt
import pytest

from app import create_app, db as _db
from app.models import User


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['MAX_LOGIN_ATTEMPTS'] = 5
    return app


@pytest.fixture
def db(app):
    """Create database tables for testing."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app, db):
    """Create test client with database ready."""
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def test_user(app, db):
    """Create a test user with a known password."""
    with app.app_context():
        password = 'TestPassword123'
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = User(
            username='TestUserA',
            email='testuser@example.com',
            password_hash=password_hash.decode('utf-8'),
            is_active=True,
            failed_login_attempts=0,
        )
        _db.session.add(user)
        _db.session.commit()
        return user


class TestLogin:
    """Tests for POST /api/auth/login."""

    def test_login_success(self, client, test_user):
        """Successful login returns 200 and user info."""
        response = client.post('/api/auth/login', json={
            'username': 'TestUserA',
            'password': 'TestPassword123',
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Login exitoso'
        assert data['user']['username'] == 'TestUserA'
        assert data['user']['email'] == 'testuser@example.com'

    def test_login_success_resets_failed_attempts(self, app, client, test_user):
        """Successful login resets failed_login_attempts to 0."""
        with app.app_context():
            user = User.query.filter_by(username='TestUserA').first()
            user.failed_login_attempts = 3
            _db.session.commit()

        client.post('/api/auth/login', json={
            'username': 'TestUserA',
            'password': 'TestPassword123',
        })

        with app.app_context():
            user = User.query.filter_by(username='TestUserA').first()
            assert user.failed_login_attempts == 0

    def test_login_success_updates_last_login(self, app, client, test_user):
        """Successful login updates last_login timestamp."""
        client.post('/api/auth/login', json={
            'username': 'TestUserA',
            'password': 'TestPassword123',
        })

        with app.app_context():
            user = User.query.filter_by(username='TestUserA').first()
            assert user.last_login is not None

    def test_login_wrong_password(self, client, test_user):
        """Wrong password returns AUTH_INVALID_CREDENTIALS."""
        response = client.post('/api/auth/login', json={
            'username': 'TestUserA',
            'password': 'WrongPassword',
        })
        assert response.status_code == 401
        data = response.get_json()
        assert data['error']['code'] == 'AUTH_INVALID_CREDENTIALS'
        assert data['error']['message'] == 'Credenciales inválidas'

    def test_login_wrong_password_increments_attempts(self, app, client, test_user):
        """Failed login increments failed_login_attempts."""
        client.post('/api/auth/login', json={
            'username': 'TestUserA',
            'password': 'WrongPassword',
        })

        with app.app_context():
            user = User.query.filter_by(username='TestUserA').first()
            assert user.failed_login_attempts == 1

    def test_login_nonexistent_user(self, client, test_user):
        """Non-existent username returns AUTH_INVALID_CREDENTIALS (no reveal)."""
        response = client.post('/api/auth/login', json={
            'username': 'NoSuchUser',
            'password': 'SomePassword',
        })
        assert response.status_code == 401
        data = response.get_json()
        assert data['error']['code'] == 'AUTH_INVALID_CREDENTIALS'

    def test_login_lockout_after_5_failures(self, app, client, test_user):
        """Account locks after 5 consecutive failed attempts."""
        for _ in range(5):
            client.post('/api/auth/login', json={
                'username': 'TestUserA',
                'password': 'WrongPassword',
            })

        with app.app_context():
            user = User.query.filter_by(username='TestUserA').first()
            assert user.failed_login_attempts == 5
            assert user.locked_until is not None

    def test_login_locked_account_returns_locked_error(self, app, client, test_user):
        """Locked account returns AUTH_ACCOUNT_LOCKED."""
        with app.app_context():
            user = User.query.filter_by(username='TestUserA').first()
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            _db.session.commit()

        response = client.post('/api/auth/login', json={
            'username': 'TestUserA',
            'password': 'TestPassword123',
        })
        assert response.status_code == 403
        data = response.get_json()
        assert data['error']['code'] == 'AUTH_ACCOUNT_LOCKED'
        assert data['error']['message'] == 'Cuenta bloqueada temporalmente'

    def test_login_expired_lockout_allows_login(self, app, client, test_user):
        """Expired lockout allows successful login."""
        with app.app_context():
            user = User.query.filter_by(username='TestUserA').first()
            user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
            user.failed_login_attempts = 5
            _db.session.commit()

        response = client.post('/api/auth/login', json={
            'username': 'TestUserA',
            'password': 'TestPassword123',
        })
        assert response.status_code == 200

    def test_login_missing_body(self, client, test_user):
        """Missing request body returns error (400 or 401)."""
        response = client.post('/api/auth/login',
                               content_type='application/json')
        assert response.status_code in (400, 401)

    def test_login_empty_fields(self, client, test_user):
        """Empty username/password returns error."""
        response = client.post('/api/auth/login', json={
            'username': '',
            'password': '',
        })
        assert response.status_code == 401


class TestLogout:
    """Tests for POST /api/auth/logout."""

    def test_logout_authenticated_user(self, client, test_user):
        """Authenticated user can logout successfully."""
        # First login
        client.post('/api/auth/login', json={
            'username': 'TestUserA',
            'password': 'TestPassword123',
        })

        # Then logout
        response = client.post('/api/auth/logout')
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Logout exitoso'

    def test_logout_unauthenticated_returns_401(self, client, test_user):
        """Unauthenticated user gets 401 on logout."""
        response = client.post('/api/auth/logout')
        assert response.status_code == 401
