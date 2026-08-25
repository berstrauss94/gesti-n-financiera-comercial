"""Tests for reports module - generation, comparison, filtering, and export."""
import pytest
from datetime import date, datetime, timezone
from decimal import Decimal

from app import create_app, db as _db
from app.models import (
    User, Business, DailyIncome, Salary,
    OwnerWithdrawal, VariableExpense, OperatingCost,
)


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
    """Create an authenticated client with a selected business."""
    with app.test_client() as client:
        with app.app_context():
            # Create user
            from bcrypt import hashpw, gensalt
            user = User(
                username='TestUser1',
                email='test@example.com',
                password_hash=hashpw(b'Password1', gensalt()).decode('utf-8'),
                phone='1234567890',
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

            # Login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['active_business_id'] = business.id
                sess['last_activity'] = datetime.now(timezone.utc).isoformat()

            yield client, business.id


@pytest.fixture
def seeded_data(app, db, authenticated_client):
    """Seed financial data for report testing."""
    client, business_id = authenticated_client

    with app.app_context():
        # Incomes
        for day in range(1, 11):
            income = DailyIncome(
                business_id=business_id,
                date=date(2024, 1, day),
                amount=Decimal('1000.00'),
                notes=f'Venta día {day}',
            )
            db.session.add(income)

        # Salaries
        salary = Salary(
            business_id=business_id,
            employee_name='Juan Pérez',
            amount=Decimal('2000.00'),
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 15),
        )
        db.session.add(salary)

        # Owner withdrawals
        withdrawal = OwnerWithdrawal(
            business_id=business_id,
            amount=Decimal('500.00'),
            date=date(2024, 1, 5),
            description='Retiro personal enero',
        )
        db.session.add(withdrawal)

        # Variable expenses
        variable = VariableExpense(
            business_id=business_id,
            category='comisiones',
            amount=Decimal('300.00'),
            date=date(2024, 1, 3),
            description='Comisión vendedor',
        )
        db.session.add(variable)

        variable2 = VariableExpense(
            business_id=business_id,
            category='servicios',
            amount=Decimal('150.00'),
            date=date(2024, 1, 7),
            description='Servicio de limpieza',
        )
        db.session.add(variable2)

        # Operating costs
        operating = OperatingCost(
            business_id=business_id,
            category='electricidad',
            amount=Decimal('200.00'),
            month=date(2024, 1, 1),
            description='Factura eléctrica enero',
        )
        db.session.add(operating)

        db.session.commit()

    return client, business_id


# ===== Task 11.1: Report generation by period =====

class TestReportGeneration:
    """Tests for GET /api/reports endpoint."""

    def test_generate_monthly_report(self, seeded_data):
        """Report with monthly granularity returns correct structure."""
        client, _ = seeded_data
        response = client.get(
            '/api/reports?granularity=monthly&from=2024-01-01&to=2024-01-31'
        )
        assert response.status_code == 200
        data = response.get_json()
        report = data['report']

        assert report['granularity'] == 'monthly'
        assert report['period_from'] == '2024-01-01'
        assert report['period_to'] == '2024-01-31'
        assert 'summary' in report
        assert 'averages' in report
        assert 'trend' in report
        assert 'groups' in report

    def test_report_summary_totals(self, seeded_data):
        """Report summary has correct totals."""
        client, _ = seeded_data
        response = client.get(
            '/api/reports?granularity=monthly&from=2024-01-01&to=2024-01-15'
        )
        data = response.get_json()
        summary = data['report']['summary']

        # 10 days * 1000 = 10000
        assert summary['total_income'] == 10000.0
        assert summary['total_salaries'] == 2000.0
        assert summary['total_withdrawals'] == 500.0
        assert summary['total_variable_expenses'] == 450.0  # 300 + 150
        assert summary['total_operating_costs'] == 200.0
        assert summary['net_profit'] == 6850.0  # 10000 - 2000 - 500 - 450 - 200

    def test_report_with_daily_granularity(self, seeded_data):
        """Daily granularity creates a group per day."""
        client, _ = seeded_data
        response = client.get(
            '/api/reports?granularity=daily&from=2024-01-01&to=2024-01-03'
        )
        data = response.get_json()
        groups = data['report']['groups']

        # Should have at least entries for days with data
        assert len(groups) >= 2

    def test_report_invalid_granularity(self, seeded_data):
        """Invalid granularity returns 400."""
        client, _ = seeded_data
        response = client.get(
            '/api/reports?granularity=invalid&from=2024-01-01&to=2024-01-31'
        )
        assert response.status_code == 400

    def test_report_missing_dates(self, seeded_data):
        """Missing from/to returns 400."""
        client, _ = seeded_data
        response = client.get('/api/reports?granularity=monthly')
        assert response.status_code == 400

    def test_report_date_from_after_to(self, seeded_data):
        """from > to returns 400."""
        client, _ = seeded_data
        response = client.get(
            '/api/reports?granularity=monthly&from=2024-02-01&to=2024-01-01'
        )
        assert response.status_code == 400

    def test_report_requires_business(self, client, db):
        """Endpoint requires active business (403 without one)."""
        response = client.get(
            '/api/reports?granularity=monthly&from=2024-01-01&to=2024-01-31'
        )
        # Should be either 401 (not logged in) or 403 (no business)
        assert response.status_code in (401, 403)


# ===== Task 11.2: Period comparison =====

class TestPeriodComparison:
    """Tests for GET /api/reports/compare endpoint."""

    def test_compare_two_periods(self, seeded_data, app, db):
        """Comparison returns correct metrics with absolute and percentage diffs."""
        client, business_id = seeded_data

        # Add data for a second period (February)
        with app.app_context():
            for day in range(1, 11):
                income = DailyIncome(
                    business_id=business_id,
                    date=date(2024, 2, day),
                    amount=Decimal('1500.00'),  # Higher than Jan
                )
                db.session.add(income)
            db.session.commit()

        response = client.get(
            '/api/reports/compare?period1_from=2024-01-01&period1_to=2024-01-31'
            '&period2_from=2024-02-01&period2_to=2024-02-29'
        )
        assert response.status_code == 200
        data = response.get_json()
        comparison = data['comparison']

        assert comparison['period1']['from'] == '2024-01-01'
        assert comparison['period2']['from'] == '2024-02-01'
        assert 'metrics' in comparison

        metrics = comparison['metrics']
        assert 'total_income' in metrics
        assert 'net_profit' in metrics

        # Period 2 income is higher
        income_metric = metrics['total_income']
        assert income_metric['period2'] > income_metric['period1']
        assert income_metric['absolute_diff'] > 0
        assert income_metric['percentage_diff'] is not None

    def test_compare_division_by_zero(self, app, db, authenticated_client):
        """When period1 value is 0, percentage_diff should be None."""
        client, business_id = authenticated_client

        # Only add data for period 2
        with app.app_context():
            income = DailyIncome(
                business_id=business_id,
                date=date(2024, 3, 1),
                amount=Decimal('5000.00'),
            )
            db.session.add(income)
            db.session.commit()

        response = client.get(
            '/api/reports/compare?period1_from=2024-01-01&period1_to=2024-01-31'
            '&period2_from=2024-03-01&period2_to=2024-03-31'
        )
        assert response.status_code == 200
        data = response.get_json()
        metrics = data['comparison']['metrics']

        # Period 1 income is 0, so percentage_diff should be None
        assert metrics['total_income']['period1'] == 0
        assert metrics['total_income']['percentage_diff'] is None

    def test_compare_missing_params(self, seeded_data):
        """Missing period params returns 400."""
        client, _ = seeded_data
        response = client.get('/api/reports/compare?period1_from=2024-01-01')
        assert response.status_code == 400


# ===== Task 11.3: Text filter =====

class TestTextFilter:
    """Tests for text filter in GET /api/reports."""

    def test_filter_by_category(self, seeded_data):
        """Filter matches category name (case-insensitive)."""
        client, _ = seeded_data
        response = client.get(
            '/api/reports?granularity=monthly&from=2024-01-01&to=2024-01-31&filter=comisiones'
        )
        assert response.status_code == 200
        data = response.get_json()
        report = data['report']

        assert report['filter_applied'] == 'comisiones'
        # Only the variable expense with category 'comisiones' should appear
        assert report['summary']['total_variable_expenses'] == 300.0

    def test_filter_by_description(self, seeded_data):
        """Filter matches description text (case-insensitive)."""
        client, _ = seeded_data
        response = client.get(
            '/api/reports?granularity=monthly&from=2024-01-01&to=2024-01-31&filter=limpieza'
        )
        assert response.status_code == 200
        data = response.get_json()
        report = data['report']

        # Only 'Servicio de limpieza' matches
        assert report['summary']['total_variable_expenses'] == 150.0

    def test_filter_case_insensitive(self, seeded_data):
        """Filter is case-insensitive."""
        client, _ = seeded_data
        response = client.get(
            '/api/reports?granularity=monthly&from=2024-01-01&to=2024-01-31&filter=COMISIONES'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['report']['summary']['total_variable_expenses'] == 300.0

    def test_filter_no_match(self, seeded_data):
        """Filter with no matches returns zero totals."""
        client, _ = seeded_data
        response = client.get(
            '/api/reports?granularity=monthly&from=2024-01-01&to=2024-01-31&filter=nonexistent'
        )
        assert response.status_code == 200
        data = response.get_json()
        summary = data['report']['summary']
        assert summary['total_income'] == 0
        assert summary['total_variable_expenses'] == 0


# ===== Task 11.4: PDF and CSV export =====

class TestExport:
    """Tests for GET /api/reports/export endpoint."""

    def test_export_csv(self, seeded_data):
        """CSV export returns valid CSV content."""
        client, _ = seeded_data
        response = client.get(
            '/api/reports/export?format=csv&from=2024-01-01&to=2024-01-31'
        )
        assert response.status_code == 200
        assert 'text/csv' in response.content_type
        assert 'attachment' in response.headers.get('Content-Disposition', '')

        # Verify CSV content
        csv_content = response.data.decode('utf-8')
        assert 'Reporte Financiero' in csv_content
        assert '10000' in csv_content  # total income appears somewhere

    def test_export_pdf(self, seeded_data):
        """PDF export returns valid PDF content."""
        client, _ = seeded_data
        response = client.get(
            '/api/reports/export?format=pdf&from=2024-01-01&to=2024-01-31'
        )
        assert response.status_code == 200
        assert 'application/pdf' in response.content_type
        assert 'attachment' in response.headers.get('Content-Disposition', '')
        # PDF starts with %PDF
        assert response.data[:4] == b'%PDF'

    def test_export_invalid_format(self, seeded_data):
        """Invalid format returns 400."""
        client, _ = seeded_data
        response = client.get(
            '/api/reports/export?format=excel&from=2024-01-01&to=2024-01-31'
        )
        assert response.status_code == 400

    def test_export_missing_dates(self, seeded_data):
        """Missing dates returns 400."""
        client, _ = seeded_data
        response = client.get('/api/reports/export?format=csv')
        assert response.status_code == 400
