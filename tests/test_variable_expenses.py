"""Tests for variable expenses CRUD endpoints."""
import pytest
from app import create_app, db as _db
from app.models import User, Business, VariableExpense


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
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
    """Create an authenticated client with an active business."""
    import uuid
    with app.test_client() as client:
        with app.app_context():
            # Create user with unique values to avoid constraint conflicts
            from bcrypt import hashpw, gensalt
            unique_id = uuid.uuid4().hex[:8]
            user = User(
                username=f'TestUser{unique_id}',
                email=f'test_{unique_id}@example.com',
                password_hash=hashpw(b'password123', gensalt()).decode('utf-8'),
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()

            # Create business
            business = Business(
                name='Test Business',
                owner_id=user.id,
                is_active=True,
            )
            db.session.add(business)
            db.session.commit()

            # Login to set session
            with client.session_transaction() as sess:
                from datetime import datetime, timezone
                sess['_user_id'] = str(user.id)
                sess['active_business_id'] = business.id
                sess['last_activity'] = datetime.now(timezone.utc).isoformat()

            yield client, business.id


class TestCreateVariableExpense:
    """Tests for POST /api/variable-expenses."""

    def test_create_valid_expense(self, authenticated_client):
        """Create a valid variable expense."""
        client, business_id = authenticated_client
        response = client.post('/api/variable-expenses', json={
            'category': 'comisiones',
            'amount': 500.00,
            'date': '2024-01-15',
            'description': 'Comisión vendedor',
        })

        assert response.status_code == 201
        data = response.get_json()
        assert 'variable_expense' in data
        expense = data['variable_expense']
        assert expense['category'] == 'comisiones'
        assert expense['amount'] == '500.00'
        assert expense['date'] == '2024-01-15'
        assert expense['description'] == 'Comisión vendedor'
        assert expense['business_id'] == business_id

    def test_create_all_valid_categories(self, authenticated_client):
        """All 8 valid categories should be accepted."""
        client, _ = authenticated_client
        categories = [
            'comisiones', 'mermas', 'servicios', 'insumos',
            'mantenimiento', 'impuestos_municipales', 'seguros', 'logistica',
        ]
        for cat in categories:
            response = client.post('/api/variable-expenses', json={
                'category': cat,
                'amount': 100.00,
                'date': '2024-01-15',
            })
            assert response.status_code == 201, f"Category '{cat}' should be accepted"

    def test_reject_invalid_category(self, authenticated_client):
        """Invalid categories should be rejected with VALIDATION_INVALID_CATEGORY."""
        client, _ = authenticated_client
        response = client.post('/api/variable-expenses', json={
            'category': 'invalid_category',
            'amount': 100.00,
            'date': '2024-01-15',
        })

        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_INVALID_CATEGORY'
        assert data['error']['field'] == 'category'

    def test_reject_empty_body(self, authenticated_client):
        """Empty request body should return 400."""
        client, _ = authenticated_client
        response = client.post('/api/variable-expenses',
                               data='',
                               content_type='application/json')
        assert response.status_code == 400

    def test_reject_invalid_amount(self, authenticated_client):
        """Amounts outside range should be rejected."""
        client, _ = authenticated_client
        response = client.post('/api/variable-expenses', json={
            'category': 'mermas',
            'amount': 0.00,
            'date': '2024-01-15',
        })
        assert response.status_code == 400

    def test_create_without_description(self, authenticated_client):
        """Description is optional."""
        client, _ = authenticated_client
        response = client.post('/api/variable-expenses', json={
            'category': 'logistica',
            'amount': 250.50,
            'date': '2024-03-01',
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['variable_expense']['description'] is None

    def test_requires_business(self, app, db, client):
        """Should return 403 if no business is selected."""
        response = client.post('/api/variable-expenses', json={
            'category': 'servicios',
            'amount': 100.00,
            'date': '2024-01-15',
        })
        # Either 401 (not logged in) or 403 (no business)
        assert response.status_code in (401, 403)


class TestListVariableExpenses:
    """Tests for GET /api/variable-expenses."""

    def test_list_all_expenses(self, authenticated_client, db):
        """List all variable expenses for the business."""
        client, business_id = authenticated_client

        # Create some expenses directly
        from datetime import date
        for cat in ['comisiones', 'mermas', 'servicios']:
            expense = VariableExpense(
                business_id=business_id,
                category=cat,
                amount=100.00,
                date=date(2024, 1, 15),
            )
            db.session.add(expense)
        db.session.commit()

        response = client.get('/api/variable-expenses')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['variable_expenses']) == 3

    def test_filter_by_category(self, authenticated_client, db):
        """Filter expenses by category."""
        client, business_id = authenticated_client

        from datetime import date
        for cat in ['comisiones', 'comisiones', 'mermas']:
            expense = VariableExpense(
                business_id=business_id,
                category=cat,
                amount=100.00,
                date=date(2024, 1, 15),
            )
            db.session.add(expense)
        db.session.commit()

        response = client.get('/api/variable-expenses?category=comisiones')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['variable_expenses']) == 2
        assert all(e['category'] == 'comisiones' for e in data['variable_expenses'])

    def test_filter_by_invalid_category(self, authenticated_client):
        """Invalid category query param should return 400."""
        client, _ = authenticated_client
        response = client.get('/api/variable-expenses?category=not_real')
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_INVALID_CATEGORY'

    def test_filter_by_date_range(self, authenticated_client, db):
        """Filter expenses by date range."""
        client, business_id = authenticated_client

        from datetime import date
        dates = [date(2024, 1, 10), date(2024, 1, 20), date(2024, 2, 5)]
        for d in dates:
            expense = VariableExpense(
                business_id=business_id,
                category='insumos',
                amount=100.00,
                date=d,
            )
            db.session.add(expense)
        db.session.commit()

        response = client.get('/api/variable-expenses?from=2024-01-15&to=2024-01-25')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['variable_expenses']) == 1
        assert data['variable_expenses'][0]['date'] == '2024-01-20'

    def test_filter_invalid_date_format(self, authenticated_client):
        """Invalid date format should return 400."""
        client, _ = authenticated_client
        response = client.get('/api/variable-expenses?from=not-a-date')
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_INVALID_INPUT'

    def test_empty_result(self, authenticated_client):
        """Should return empty list if no expenses match."""
        client, _ = authenticated_client
        response = client.get('/api/variable-expenses')
        assert response.status_code == 200
        data = response.get_json()
        assert data['variable_expenses'] == []
