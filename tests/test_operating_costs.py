"""Tests for operating costs CRUD endpoints."""
import pytest
from app import create_app, db as _db
from app.models.business import Business
from app.models.user import User
from app.models.expense import OperatingCost


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SESSION_TIMEOUT_MINUTES'] = 9999
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
def client(app):
    """Create test client."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_client(app, db):
    """Create an authenticated client with active business."""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            from datetime import datetime, timezone
            # Create a user and business
            user = User(username='TestUser1', email='test@example.com', password_hash='x')
            db.session.add(user)
            db.session.commit()

            business = Business(name='Test Business', owner_id=user.id)
            db.session.add(business)
            db.session.commit()

            sess['active_business_id'] = business.id
            sess['_user_id'] = str(user.id)
            sess['last_activity'] = datetime.now(timezone.utc).isoformat()
        yield client, business.id


class TestCreateOperatingCost:
    """Tests for POST /api/operating-costs."""

    def test_create_valid_operating_cost(self, authenticated_client, db):
        """Should create operating cost with valid data."""
        client, business_id = authenticated_client
        response = client.post('/api/operating-costs', json={
            'category': 'electricidad',
            'amount': 5000.00,
            'month': '2024-01-01',
            'description': 'Factura enero',
        })
        assert response.status_code == 201
        data = response.get_json()
        assert 'operating_cost' in data
        assert data['operating_cost']['category'] == 'electricidad'
        assert data['operating_cost']['amount'] == '5000.00'
        assert data['operating_cost']['month'] == '2024-01-01'
        assert data['operating_cost']['description'] == 'Factura enero'
        assert data['operating_cost']['business_id'] == business_id

    def test_create_all_valid_categories(self, authenticated_client, db):
        """Should accept all 5 valid operating cost categories."""
        client, _ = authenticated_client
        categories = ['electricidad', 'monotributo', 'mercaderia', 'alquiler', 'contable']
        for cat in categories:
            response = client.post('/api/operating-costs', json={
                'category': cat,
                'amount': 1000.00,
                'month': '2024-02-01',
            })
            assert response.status_code == 201, f"Failed for category: {cat}"

    def test_create_invalid_category(self, authenticated_client, db):
        """Should reject invalid category with VALIDATION_INVALID_CATEGORY."""
        client, _ = authenticated_client
        response = client.post('/api/operating-costs', json={
            'category': 'comida',
            'amount': 1000.00,
            'month': '2024-01-01',
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_INVALID_CATEGORY'

    def test_create_missing_body(self, authenticated_client, db):
        """Should return 400 when no body is provided."""
        client, _ = authenticated_client
        response = client.post('/api/operating-costs',
                               content_type='application/json')
        assert response.status_code == 400

    def test_create_invalid_amount(self, authenticated_client, db):
        """Should reject amount outside valid range."""
        client, _ = authenticated_client
        response = client.post('/api/operating-costs', json={
            'category': 'alquiler',
            'amount': 0,
            'month': '2024-01-01',
        })
        assert response.status_code == 400

    def test_create_without_description(self, authenticated_client, db):
        """Should allow creating cost without description."""
        client, _ = authenticated_client
        response = client.post('/api/operating-costs', json={
            'category': 'contable',
            'amount': 3000.00,
            'month': '2024-03-01',
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['operating_cost']['description'] is None


class TestListOperatingCosts:
    """Tests for GET /api/operating-costs."""

    def test_list_empty(self, authenticated_client, db):
        """Should return empty list when no costs exist."""
        client, _ = authenticated_client
        response = client.get('/api/operating-costs')
        assert response.status_code == 200
        data = response.get_json()
        assert data['operating_costs'] == []

    def test_list_all_costs(self, authenticated_client, db):
        """Should return all operating costs for the business."""
        client, business_id = authenticated_client
        # Create some costs
        for cat in ['electricidad', 'alquiler']:
            client.post('/api/operating-costs', json={
                'category': cat,
                'amount': 2000.00,
                'month': '2024-01-01',
            })
        response = client.get('/api/operating-costs')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['operating_costs']) == 2

    def test_list_filter_by_month(self, authenticated_client, db):
        """Should filter operating costs by month."""
        client, _ = authenticated_client
        # Create costs in different months
        client.post('/api/operating-costs', json={
            'category': 'electricidad',
            'amount': 5000.00,
            'month': '2024-01-01',
        })
        client.post('/api/operating-costs', json={
            'category': 'electricidad',
            'amount': 5500.00,
            'month': '2024-02-01',
        })

        response = client.get('/api/operating-costs?month=2024-01-01')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['operating_costs']) == 1
        assert data['operating_costs'][0]['month'] == '2024-01-01'

    def test_list_invalid_month_format(self, authenticated_client, db):
        """Should return 400 for invalid month format."""
        client, _ = authenticated_client
        response = client.get('/api/operating-costs?month=invalid')
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_INVALID_INPUT'
