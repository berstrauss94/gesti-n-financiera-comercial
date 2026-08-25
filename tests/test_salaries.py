"""Tests for employee salary CRUD endpoints."""
import pytest
from decimal import Decimal
from datetime import date, datetime, timezone

from app import create_app, db as _db
from app.models.user import User
from app.models.business import Business
from app.models.expense import Salary


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SESSION_TIMEOUT_MINUTES'] = 9999  # Disable timeout for tests
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    """Provide database session."""
    return _db


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def auth_user(db):
    """Create a test user."""
    import bcrypt
    password_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(username='TestUser1', email='test@example.com', password_hash=password_hash)
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
        sess['last_activity'] = datetime.now(timezone.utc).isoformat()
    return client


class TestCreateSalary:
    """Tests for POST /api/salaries."""

    def test_create_salary_success(self, logged_in_client, business, db):
        """Create salary with valid data returns 201."""
        response = logged_in_client.post('/api/salaries', json={
            'employee_name': 'Juan Pérez',
            'amount': 50000.00,
            'period_start': '2024-01-01',
            'period_end': '2024-01-31',
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['salary']['employee_name'] == 'Juan Pérez'
        assert data['salary']['amount'] == '50000.00'
        assert data['salary']['period_start'] == '2024-01-01'
        assert data['salary']['period_end'] == '2024-01-31'
        assert data['salary']['business_id'] == business.id

    def test_create_salary_missing_employee_name(self, logged_in_client, db):
        """Missing employee_name returns 400."""
        response = logged_in_client.post('/api/salaries', json={
            'amount': 50000.00,
            'period_start': '2024-01-01',
            'period_end': '2024-01-31',
        })
        assert response.status_code == 400

    def test_create_salary_amount_too_low(self, logged_in_client, db):
        """Amount below 0.01 returns validation error."""
        response = logged_in_client.post('/api/salaries', json={
            'employee_name': 'Test Employee',
            'amount': 0.00,
            'period_start': '2024-01-01',
            'period_end': '2024-01-31',
        })
        assert response.status_code == 400

    def test_create_salary_amount_too_high(self, logged_in_client, db):
        """Amount above 999999999.99 returns validation error."""
        response = logged_in_client.post('/api/salaries', json={
            'employee_name': 'Test Employee',
            'amount': 9999999999.99,
            'period_start': '2024-01-01',
            'period_end': '2024-01-31',
        })
        assert response.status_code == 400

    def test_create_salary_min_amount(self, logged_in_client, db):
        """Minimum valid amount 0.01 succeeds."""
        response = logged_in_client.post('/api/salaries', json={
            'employee_name': 'Employee',
            'amount': 0.01,
            'period_start': '2024-01-01',
            'period_end': '2024-01-31',
        })
        assert response.status_code == 201

    def test_create_salary_no_body(self, logged_in_client, db):
        """Missing request body returns 400."""
        response = logged_in_client.post('/api/salaries',
                                         content_type='application/json')
        assert response.status_code == 400

    def test_create_salary_no_business_selected(self, client, auth_user):
        """Without active business returns 403."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
            sess['last_activity'] = datetime.now(timezone.utc).isoformat()
        response = client.post('/api/salaries', json={
            'employee_name': 'Test',
            'amount': 1000.00,
            'period_start': '2024-01-01',
            'period_end': '2024-01-31',
        })
        assert response.status_code == 403


class TestListSalaries:
    """Tests for GET /api/salaries."""

    def test_list_all_salaries(self, logged_in_client, business, db):
        """List all salaries for the active business."""
        db.session.add(Salary(
            business_id=business.id,
            employee_name='Employee 1',
            amount=Decimal('30000.00'),
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
        ))
        db.session.add(Salary(
            business_id=business.id,
            employee_name='Employee 2',
            amount=Decimal('40000.00'),
            period_start=date(2024, 2, 1),
            period_end=date(2024, 2, 29),
        ))
        db.session.commit()

        response = logged_in_client.get('/api/salaries')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['salaries']) == 2

    def test_list_salaries_filter_by_period(self, logged_in_client, business, db):
        """Filter salaries by period overlap."""
        # January salary
        db.session.add(Salary(
            business_id=business.id,
            employee_name='Employee 1',
            amount=Decimal('30000.00'),
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
        ))
        # February salary
        db.session.add(Salary(
            business_id=business.id,
            employee_name='Employee 2',
            amount=Decimal('40000.00'),
            period_start=date(2024, 2, 1),
            period_end=date(2024, 2, 29),
        ))
        db.session.commit()

        # Query for January only
        response = logged_in_client.get('/api/salaries?period=2024-01-01,2024-01-31')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['salaries']) == 1
        assert data['salaries'][0]['employee_name'] == 'Employee 1'

    def test_list_salaries_period_overlap(self, logged_in_client, business, db):
        """Period filter returns salaries that overlap the range."""
        # Salary spanning Jan-Feb
        db.session.add(Salary(
            business_id=business.id,
            employee_name='Employee 1',
            amount=Decimal('30000.00'),
            period_start=date(2024, 1, 15),
            period_end=date(2024, 2, 15),
        ))
        db.session.commit()

        # Query for January - should include since it overlaps
        response = logged_in_client.get('/api/salaries?period=2024-01-01,2024-01-31')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['salaries']) == 1

    def test_list_salaries_invalid_period_format(self, logged_in_client, db):
        """Invalid period format returns 400."""
        response = logged_in_client.get('/api/salaries?period=invalid')
        assert response.status_code == 200  # Single part just gets ignored, no split match
        # With two parts but invalid dates
        response = logged_in_client.get('/api/salaries?period=abc,def')
        assert response.status_code == 400

    def test_list_salaries_multi_tenant_isolation(self, logged_in_client, business, db, auth_user):
        """Salaries from another business are not visible."""
        other_biz = Business(name='Otro Negocio', owner_id=auth_user.id)
        db.session.add(other_biz)
        db.session.commit()

        # Add salary to active business
        db.session.add(Salary(
            business_id=business.id,
            employee_name='My Employee',
            amount=Decimal('30000.00'),
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
        ))
        # Add salary to other business
        db.session.add(Salary(
            business_id=other_biz.id,
            employee_name='Other Employee',
            amount=Decimal('50000.00'),
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
        ))
        db.session.commit()

        response = logged_in_client.get('/api/salaries')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['salaries']) == 1
        assert data['salaries'][0]['employee_name'] == 'My Employee'
