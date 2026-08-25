"""Tests for daily gross income CRUD endpoints."""
import pytest
from decimal import Decimal
from datetime import date

from app import create_app, db as _db
from app.models.user import User
from app.models.business import Business
from app.models.income import DailyIncome


@pytest.fixture
def app():
    """Create application for testing."""
    import os
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SESSION_TIMEOUT_MINUTES'] = 9999  # Disable timeout for tests
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
def auth_user(db):
    """Create a test user."""
    user = User(
        username='TestUser1',
        email='test@example.com',
        password_hash='fake_hash_for_testing',
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def business(db, auth_user):
    """Create a test business."""
    biz = Business(name='Mi Negocio', owner_id=auth_user.id)
    db.session.add(biz)
    db.session.commit()
    return biz


@pytest.fixture
def logged_in_client(client, auth_user, business):
    """Client with authenticated user and active business."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(auth_user.id)
        sess['active_business_id'] = business.id
        from datetime import datetime, timezone
        sess['last_activity'] = datetime.now(timezone.utc).isoformat()
    return client


class TestCreateIncome:
    """Tests for POST /api/income."""

    def test_create_income_success(self, logged_in_client, business, db):
        """Create income with valid data returns 201."""
        response = logged_in_client.post('/api/income', json={
            'amount': 1500.50,
            'date': '2024-01-15',
            'notes': 'Venta del día',
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['income']['amount'] == '1500.50'
        assert data['income']['date'] == '2024-01-15'
        assert data['income']['notes'] == 'Venta del día'
        assert data['income']['business_id'] == business.id

    def test_create_income_no_notes(self, logged_in_client, db):
        """Create income without notes succeeds."""
        response = logged_in_client.post('/api/income', json={
            'amount': 100.00,
            'date': '2024-02-01',
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['income']['notes'] is None

    def test_create_income_duplicate_date_returns_409(self, logged_in_client, business, db):
        """Duplicate date+business returns 409 INCOME_DUPLICATE_DATE."""
        # First income
        logged_in_client.post('/api/income', json={
            'amount': 1000.00,
            'date': '2024-01-15',
        })
        # Duplicate
        response = logged_in_client.post('/api/income', json={
            'amount': 2000.00,
            'date': '2024-01-15',
        })
        assert response.status_code == 409
        data = response.get_json()
        assert data['error']['code'] == 'INCOME_DUPLICATE_DATE'

    def test_create_income_amount_too_low(self, logged_in_client, db):
        """Amount below 0.01 returns validation error."""
        response = logged_in_client.post('/api/income', json={
            'amount': 0.00,
            'date': '2024-01-15',
        })
        assert response.status_code == 400

    def test_create_income_amount_too_high(self, logged_in_client, db):
        """Amount above 999999999.99 returns validation error."""
        response = logged_in_client.post('/api/income', json={
            'amount': 9999999999.99,
            'date': '2024-01-15',
        })
        assert response.status_code == 400

    def test_create_income_min_amount(self, logged_in_client, db):
        """Minimum valid amount 0.01 succeeds."""
        response = logged_in_client.post('/api/income', json={
            'amount': 0.01,
            'date': '2024-01-15',
        })
        assert response.status_code == 201

    def test_create_income_max_amount(self, logged_in_client, db):
        """Maximum valid amount 999999999.99 succeeds."""
        response = logged_in_client.post('/api/income', json={
            'amount': 999999999.99,
            'date': '2024-03-01',
        })
        assert response.status_code == 201

    def test_create_income_no_body(self, logged_in_client, db):
        """Missing request body returns 400."""
        response = logged_in_client.post('/api/income',
                                         content_type='application/json')
        assert response.status_code == 400

    def test_create_income_no_business_selected(self, client, auth_user):
        """Without active business returns 403."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
            from datetime import datetime, timezone
            sess['last_activity'] = datetime.now(timezone.utc).isoformat()
        response = client.post('/api/income', json={
            'amount': 100.00,
            'date': '2024-01-15',
        })
        assert response.status_code == 403


class TestQueryIncome:
    """Tests for GET /api/income."""

    def test_query_by_date(self, logged_in_client, business, db):
        """Query income by specific date returns the record."""
        income = DailyIncome(
            business_id=business.id,
            date=date(2024, 1, 15),
            amount=Decimal('1500.00'),
        )
        db.session.add(income)
        db.session.commit()

        response = logged_in_client.get('/api/income?date=2024-01-15')
        assert response.status_code == 200
        data = response.get_json()
        assert data['income'] is not None
        assert data['income']['date'] == '2024-01-15'

    def test_query_by_date_not_found(self, logged_in_client, db):
        """Query date with no income returns null."""
        response = logged_in_client.get('/api/income?date=2024-12-31')
        assert response.status_code == 200
        data = response.get_json()
        assert data['income'] is None

    def test_query_by_date_range(self, logged_in_client, business, db):
        """Query income by date range returns matching records."""
        for day in [10, 12, 15, 20]:
            db.session.add(DailyIncome(
                business_id=business.id,
                date=date(2024, 1, day),
                amount=Decimal('1000.00'),
            ))
        db.session.commit()

        response = logged_in_client.get('/api/income?from=2024-01-10&to=2024-01-15')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['incomes']) == 3  # 10, 12, 15

    def test_query_range_invalid_order(self, logged_in_client, db):
        """from > to returns 400."""
        response = logged_in_client.get('/api/income?from=2024-01-20&to=2024-01-10')
        assert response.status_code == 400

    def test_query_invalid_date_format(self, logged_in_client, db):
        """Invalid date format returns 400."""
        response = logged_in_client.get('/api/income?date=15-01-2024')
        assert response.status_code == 400

    def test_query_all_no_params(self, logged_in_client, business, db):
        """No query params returns all income for business."""
        db.session.add(DailyIncome(
            business_id=business.id,
            date=date(2024, 1, 1),
            amount=Decimal('500.00'),
        ))
        db.session.commit()

        response = logged_in_client.get('/api/income')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['incomes']) == 1

    def test_query_multi_tenant_isolation(self, logged_in_client, business, db, auth_user):
        """Income from another business is not visible."""
        # Create another business
        other_biz = Business(name='Otro Negocio', owner_id=auth_user.id)
        db.session.add(other_biz)
        db.session.commit()

        # Add income to both businesses
        db.session.add(DailyIncome(
            business_id=business.id,
            date=date(2024, 1, 1),
            amount=Decimal('1000.00'),
        ))
        db.session.add(DailyIncome(
            business_id=other_biz.id,
            date=date(2024, 1, 1),
            amount=Decimal('2000.00'),
        ))
        db.session.commit()

        response = logged_in_client.get('/api/income')
        assert response.status_code == 200
        data = response.get_json()
        # Only shows the active business's income
        assert len(data['incomes']) == 1
        assert data['incomes'][0]['business_id'] == business.id


class TestUpdateIncome:
    """Tests for PUT /api/income/:id."""

    def test_update_income_success(self, logged_in_client, business, db):
        """Update income with valid data returns 200."""
        income = DailyIncome(
            business_id=business.id,
            date=date(2024, 1, 15),
            amount=Decimal('1000.00'),
            notes='Original',
        )
        db.session.add(income)
        db.session.commit()

        response = logged_in_client.put(f'/api/income/{income.id}', json={
            'amount': 2000.00,
            'date': '2024-01-15',
            'notes': 'Actualizado',
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['income']['amount'] == '2000.00'
        assert data['income']['notes'] == 'Actualizado'

    def test_update_income_not_found(self, logged_in_client, db):
        """Update non-existent income returns 404."""
        response = logged_in_client.put('/api/income/9999', json={
            'amount': 100.00,
            'date': '2024-01-15',
        })
        assert response.status_code == 404

    def test_update_income_date_conflict_returns_409(self, logged_in_client, business, db):
        """Changing date to one that already has income returns 409."""
        inc1 = DailyIncome(
            business_id=business.id,
            date=date(2024, 1, 10),
            amount=Decimal('1000.00'),
        )
        inc2 = DailyIncome(
            business_id=business.id,
            date=date(2024, 1, 15),
            amount=Decimal('2000.00'),
        )
        db.session.add_all([inc1, inc2])
        db.session.commit()

        # Try to change inc1's date to 2024-01-15 (conflict with inc2)
        response = logged_in_client.put(f'/api/income/{inc1.id}', json={
            'amount': 1000.00,
            'date': '2024-01-15',
        })
        assert response.status_code == 409
        data = response.get_json()
        assert data['error']['code'] == 'INCOME_DUPLICATE_DATE'

    def test_update_income_with_overwrite_confirmation(self, logged_in_client, business, db):
        """With confirm_overwrite=true, overwrites conflicting record."""
        inc1 = DailyIncome(
            business_id=business.id,
            date=date(2024, 1, 10),
            amount=Decimal('1000.00'),
        )
        inc2 = DailyIncome(
            business_id=business.id,
            date=date(2024, 1, 15),
            amount=Decimal('2000.00'),
        )
        db.session.add_all([inc1, inc2])
        db.session.commit()

        response = logged_in_client.put(f'/api/income/{inc1.id}', json={
            'amount': 1500.00,
            'date': '2024-01-15',
            'confirm_overwrite': True,
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['income']['date'] == '2024-01-15'

    def test_update_income_invalid_amount(self, logged_in_client, business, db):
        """Update with invalid amount returns 400."""
        income = DailyIncome(
            business_id=business.id,
            date=date(2024, 1, 15),
            amount=Decimal('1000.00'),
        )
        db.session.add(income)
        db.session.commit()

        response = logged_in_client.put(f'/api/income/{income.id}', json={
            'amount': -5.00,
            'date': '2024-01-15',
        })
        assert response.status_code == 400
