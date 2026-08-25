"""Tests for user registration endpoint."""
import pytest
from app import create_app, db
from app.models.user import User


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 1,
        'pool_pre_ping': True,
    }
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestRegisterValidation:
    """Tests for registration input validation."""

    def test_register_username_too_short(self, client):
        """Username with fewer than 8 characters returns VALIDATION_USERNAME_LENGTH."""
        response = client.post('/api/auth/register', json={
            'username': 'Short1',
            'email': 'test@example.com',
            'password': 'securepassword',
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_USERNAME_LENGTH'
        assert data['error']['field'] == 'username'
        assert 'mínimo 8 caracteres' in data['error']['message']

    def test_register_username_no_uppercase(self, client):
        """Username without uppercase returns VALIDATION_USERNAME_UPPERCASE."""
        response = client.post('/api/auth/register', json={
            'username': 'alllowercase',
            'email': 'test@example.com',
            'password': 'securepassword',
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_USERNAME_UPPERCASE'
        assert data['error']['field'] == 'username'

    def test_register_invalid_email(self, client):
        """Invalid email returns VALIDATION_EMAIL_FORMAT."""
        response = client.post('/api/auth/register', json={
            'username': 'ValidUser1',
            'email': 'not-an-email',
            'password': 'securepassword',
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_EMAIL_FORMAT'
        assert data['error']['field'] == 'email'

    def test_register_invalid_phone_too_short(self, client):
        """Phone with fewer than 7 digits returns VALIDATION_PHONE_FORMAT."""
        response = client.post('/api/auth/register', json={
            'username': 'ValidUser1',
            'email': 'test@example.com',
            'password': 'securepassword',
            'phone': '12345',
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_PHONE_FORMAT'
        assert data['error']['field'] == 'phone'

    def test_register_invalid_phone_too_long(self, client):
        """Phone with more than 15 digits returns VALIDATION_PHONE_FORMAT."""
        response = client.post('/api/auth/register', json={
            'username': 'ValidUser1',
            'email': 'test@example.com',
            'password': 'securepassword',
            'phone': '1234567890123456',
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_PHONE_FORMAT'
        assert data['error']['field'] == 'phone'

    def test_register_no_json_body(self, client):
        """Request without JSON body returns 400."""
        response = client.post('/api/auth/register',
                               data='not json',
                               content_type='text/plain')
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_INVALID_INPUT'


class TestRegisterSuccess:
    """Tests for successful registration."""

    def test_register_success(self, client):
        """Valid registration returns 201 with user data."""
        response = client.post('/api/auth/register', json={
            'username': 'ValidUser1',
            'email': 'user@example.com',
            'password': 'securepassword',
            'phone': '+54 11 1234-5678',
        })
        assert response.status_code == 201
        data = response.get_json()
        assert 'user' in data
        assert data['user']['username'] == 'ValidUser1'
        assert data['user']['email'] == 'user@example.com'
        assert data['user']['phone'] == '+54 11 1234-5678'
        assert data['user']['is_active'] is True
        assert 'id' in data['user']
        assert 'created_at' in data['user']
        # Password hash must not be in the response
        assert 'password_hash' not in data['user']
        assert 'password' not in data['user']

    def test_register_success_without_phone(self, client):
        """Registration without phone is valid (phone is optional)."""
        response = client.post('/api/auth/register', json={
            'username': 'ValidUser1',
            'email': 'user@example.com',
            'password': 'securepassword',
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['user']['phone'] is None

    def test_register_password_is_hashed(self, client, app):
        """Password is stored as bcrypt hash, not plaintext."""
        client.post('/api/auth/register', json={
            'username': 'ValidUser1',
            'email': 'user@example.com',
            'password': 'mypassword123',
        })
        with app.app_context():
            user = User.query.filter_by(username='ValidUser1').first()
            assert user is not None
            assert user.password_hash != 'mypassword123'
            assert user.password_hash.startswith('$2b$')


class TestRegisterDuplicates:
    """Tests for duplicate username/email handling."""

    def test_register_duplicate_username(self, client):
        """Duplicate username returns 409 with DUPLICATE_USERNAME."""
        client.post('/api/auth/register', json={
            'username': 'ValidUser1',
            'email': 'first@example.com',
            'password': 'securepassword',
        })
        response = client.post('/api/auth/register', json={
            'username': 'ValidUser1',
            'email': 'second@example.com',
            'password': 'securepassword',
        })
        assert response.status_code == 409
        data = response.get_json()
        assert data['error']['code'] == 'DUPLICATE_USERNAME'
        assert data['error']['field'] == 'username'

    def test_register_duplicate_email(self, client):
        """Duplicate email returns 409 with DUPLICATE_EMAIL."""
        client.post('/api/auth/register', json={
            'username': 'ValidUser1',
            'email': 'same@example.com',
            'password': 'securepassword',
        })
        response = client.post('/api/auth/register', json={
            'username': 'ValidUser2',
            'email': 'same@example.com',
            'password': 'securepassword',
        })
        assert response.status_code == 409
        data = response.get_json()
        assert data['error']['code'] == 'DUPLICATE_EMAIL'
        assert data['error']['field'] == 'email'
