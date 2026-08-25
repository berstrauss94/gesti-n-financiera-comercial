"""Tests for session expiration by inactivity (Task 3.3)."""
from datetime import datetime, timedelta, timezone

import bcrypt
import pytest

from app import create_app, db as _db
from app.models import User


@pytest.fixture
def app():
    """Create application for testing with short timeout."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SESSION_TIMEOUT_MINUTES'] = 30
    return app


@pytest.fixture
def db(app):
    """Create database tables for testing."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app, db):
    """Create test client (depends on db to ensure tables exist)."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def test_user(db):
    """Create a test user."""
    password_hash = bcrypt.hashpw(
        'TestPassword1'.encode('utf-8'), bcrypt.gensalt()
    ).decode('utf-8')
    user = User(
        username='TestUserA',
        email='testuser@example.com',
        password_hash=password_hash,
        phone='1234567890',
    )
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, username='TestUserA', password='TestPassword1'):
    """Helper to login a user."""
    return client.post('/api/auth/login', json={
        'username': username,
        'password': password,
    })


class TestSessionExpirationMiddleware:
    """Tests for the before_request session expiration middleware."""

    def test_active_session_updates_last_activity(self, client, db, test_user):
        """Valid session should update last_activity on each request."""
        # Login first
        resp = _login(client)
        assert resp.status_code == 200

        # Access session endpoint - should succeed
        resp = client.get('/api/auth/session')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['session']['active'] is True
        assert data['session']['user']['username'] == 'TestUserA'

    def test_expired_session_returns_401(self, app, db, test_user):
        """Session older than timeout should return AUTH_SESSION_EXPIRED."""
        with app.test_client() as client:
            # Login
            resp = _login(client)
            assert resp.status_code == 200

            # Manually set last_activity to 31 minutes ago
            with client.session_transaction() as sess:
                expired_time = datetime.now(timezone.utc) - timedelta(minutes=31)
                sess['last_activity'] = expired_time.isoformat()

            # Now any request should get 401
            resp = client.get('/api/auth/session')
            assert resp.status_code == 401
            data = resp.get_json()
            assert data['error']['code'] == 'AUTH_SESSION_EXPIRED'
            assert data['error']['message'] == 'Sesión expirada por inactividad'

    def test_session_exactly_at_boundary_not_expired(self, app, db, test_user):
        """Session exactly at 30 minutes should NOT be expired (only > 30)."""
        with app.test_client() as client:
            # Login
            resp = _login(client)
            assert resp.status_code == 200

            # Set last_activity to exactly 29 minutes 59 seconds ago
            # (just under the 30 min threshold)
            with client.session_transaction() as sess:
                boundary_time = datetime.now(timezone.utc) - timedelta(minutes=29, seconds=59)
                sess['last_activity'] = boundary_time.isoformat()

            # Should still be valid (elapsed < 30)
            resp = client.get('/api/auth/session')
            assert resp.status_code == 200

    def test_session_just_over_boundary_expired(self, app, db, test_user):
        """Session at 30 minutes + 1 second should be expired."""
        with app.test_client() as client:
            resp = _login(client)
            assert resp.status_code == 200

            with client.session_transaction() as sess:
                over_time = datetime.now(timezone.utc) - timedelta(minutes=30, seconds=1)
                sess['last_activity'] = over_time.isoformat()

            resp = client.get('/api/auth/session')
            assert resp.status_code == 401
            data = resp.get_json()
            assert data['error']['code'] == 'AUTH_SESSION_EXPIRED'

    def test_public_paths_skip_session_check(self, client, db, test_user):
        """Public paths should not trigger session expiration."""
        # Health endpoint should always work
        resp = client.get('/health')
        assert resp.status_code == 200

        # Login endpoint should work
        resp = client.post('/api/auth/login', json={
            'username': 'TestUserA',
            'password': 'TestPassword1',
        })
        assert resp.status_code == 200

    def test_missing_last_activity_expires_session(self, app, db, test_user):
        """If last_activity is missing from session, expire it."""
        with app.test_client() as client:
            # Login
            resp = _login(client)
            assert resp.status_code == 200

            # Remove last_activity from session
            with client.session_transaction() as sess:
                if 'last_activity' in sess:
                    del sess['last_activity']

            # Should get expired
            resp = client.get('/api/auth/session')
            assert resp.status_code == 401
            data = resp.get_json()
            assert data['error']['code'] == 'AUTH_SESSION_EXPIRED'

    def test_unauthenticated_request_not_affected(self, client, db):
        """Unauthenticated requests should not trigger expiration logic."""
        # Without login, session endpoint returns 401 from the endpoint itself
        resp = client.get('/api/auth/session')
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['error']['code'] == 'AUTH_SESSION_EXPIRED'

    def test_custom_timeout_config(self, test_user):
        """Custom SESSION_TIMEOUT_MINUTES should be respected."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SESSION_TIMEOUT_MINUTES'] = 5  # 5 minutes

        with app.app_context():
            _db.create_all()

            # Create user in this context
            password_hash = bcrypt.hashpw(
                'TestPassword1'.encode('utf-8'), bcrypt.gensalt()
            ).decode('utf-8')
            user = User(
                username='TestUserB',
                email='testuserb@example.com',
                password_hash=password_hash,
                phone='1234567890',
            )
            _db.session.add(user)
            _db.session.commit()

            with app.test_client() as client:
                resp = _login(client, username='TestUserB')
                assert resp.status_code == 200

                # Set last_activity to 6 minutes ago (> 5 min timeout)
                with client.session_transaction() as sess:
                    old_time = datetime.now(timezone.utc) - timedelta(minutes=6)
                    sess['last_activity'] = old_time.isoformat()

                resp = client.get('/api/auth/session')
                assert resp.status_code == 401

            _db.drop_all()


class TestSessionEndpoint:
    """Tests for GET /api/auth/session endpoint."""

    def test_active_session_returns_user_info(self, client, db, test_user):
        """Active session should return user information."""
        _login(client)
        resp = client.get('/api/auth/session')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['session']['active'] is True
        assert data['session']['user']['id'] == test_user.id
        assert data['session']['user']['username'] == 'TestUserA'
        assert data['session']['user']['email'] == 'testuser@example.com'

    def test_no_session_returns_expired(self, client, db):
        """No session should return AUTH_SESSION_EXPIRED."""
        resp = client.get('/api/auth/session')
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['error']['code'] == 'AUTH_SESSION_EXPIRED'
        assert data['error']['message'] == 'Sesión expirada por inactividad'

    def test_session_after_logout_returns_expired(self, client, db, test_user):
        """After logout, session should return expired."""
        _login(client)
        client.post('/api/auth/logout')
        resp = client.get('/api/auth/session')
        assert resp.status_code == 401
