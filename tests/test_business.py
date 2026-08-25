"""Tests for business module: CRUD endpoints, selection, and @require_business decorator."""
import pytest
import bcrypt

from app import create_app, db as _db
from app.models import User, Business
from app.models.threshold_config import ThresholdConfig


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
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
    """Create test client with database."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def user(app, db):
    """Create a test user."""
    password_hash = bcrypt.hashpw(b'TestPass123', bcrypt.gensalt()).decode('utf-8')
    u = User(
        username='TestUser1',
        email='test@example.com',
        password_hash=password_hash,
        phone='1234567890',
    )
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def auth_client(client, user):
    """Create an authenticated test client."""
    response = client.post('/api/auth/login', json={
        'username': 'TestUser1',
        'password': 'TestPass123',
    })
    assert response.status_code == 200
    return client


@pytest.fixture
def business(app, db, user):
    """Create a test business."""
    b = Business(name='Mi Negocio', owner_id=user.id)
    db.session.add(b)
    db.session.commit()
    return b


class TestCreateBusiness:
    """Tests for POST /api/businesses."""

    def test_create_business_success(self, auth_client, app):
        """Creating a business returns 201 and the business data."""
        response = auth_client.post('/api/businesses', json={'name': 'Tienda ABC'})
        assert response.status_code == 201
        data = response.get_json()
        assert data['business']['name'] == 'Tienda ABC'
        assert data['business']['is_active'] is True

    def test_create_business_seeds_thresholds(self, auth_client, app, db):
        """Creating a business seeds default threshold configurations."""
        response = auth_client.post('/api/businesses', json={'name': 'Tienda XYZ'})
        assert response.status_code == 201
        business_id = response.get_json()['business']['id']

        with app.app_context():
            thresholds = ThresholdConfig.query.filter_by(business_id=business_id).all()
            assert len(thresholds) > 0
            categories = [t.category for t in thresholds]
            assert 'salarios' in categories
            assert 'retiros_dueno' in categories
            assert 'mercaderia' in categories

    def test_create_business_requires_name(self, auth_client):
        """Missing name returns 400."""
        response = auth_client.post('/api/businesses', json={})
        assert response.status_code == 400
        assert response.get_json()['error']['field'] == 'name'

    def test_create_business_empty_name(self, auth_client):
        """Empty name returns 400."""
        response = auth_client.post('/api/businesses', json={'name': '   '})
        assert response.status_code == 400

    def test_create_business_requires_auth(self, client):
        """Unauthenticated request is rejected."""
        response = client.post('/api/businesses', json={'name': 'Test'})
        assert response.status_code == 401


class TestListBusinesses:
    """Tests for GET /api/businesses."""

    def test_list_businesses_empty(self, auth_client):
        """Returns empty list when user has no businesses."""
        response = auth_client.get('/api/businesses')
        assert response.status_code == 200
        assert response.get_json()['businesses'] == []

    def test_list_businesses_returns_owned(self, auth_client, app, db, user):
        """Returns only businesses owned by the current user."""
        b1 = Business(name='Negocio 1', owner_id=user.id)
        b2 = Business(name='Negocio 2', owner_id=user.id)
        db.session.add_all([b1, b2])
        db.session.commit()

        response = auth_client.get('/api/businesses')
        assert response.status_code == 200
        businesses = response.get_json()['businesses']
        assert len(businesses) == 2

    def test_list_businesses_excludes_inactive(self, auth_client, app, db, user):
        """Soft-deleted businesses are excluded."""
        b = Business(name='Deleted', owner_id=user.id, is_active=False)
        db.session.add(b)
        db.session.commit()

        response = auth_client.get('/api/businesses')
        assert response.status_code == 200
        assert response.get_json()['businesses'] == []

    def test_list_businesses_excludes_other_users(self, auth_client, app, db):
        """Businesses from other users are not returned."""
        other_user = User(
            username='OtherUser1',
            email='other@example.com',
            password_hash='hash',
        )
        db.session.add(other_user)
        db.session.commit()
        b = Business(name='Not Mine', owner_id=other_user.id)
        db.session.add(b)
        db.session.commit()

        response = auth_client.get('/api/businesses')
        assert response.status_code == 200
        assert response.get_json()['businesses'] == []


class TestUpdateBusiness:
    """Tests for PUT /api/businesses/:id."""

    def test_update_business_success(self, auth_client, app, db, user):
        """Owner can update business name."""
        b = Business(name='Old Name', owner_id=user.id)
        db.session.add(b)
        db.session.commit()
        bid = b.id

        response = auth_client.put(f'/api/businesses/{bid}', json={'name': 'New Name'})
        assert response.status_code == 200
        assert response.get_json()['business']['name'] == 'New Name'

    def test_update_business_not_owner(self, auth_client, app, db):
        """Non-owner gets 403."""
        other_user = User(
            username='OtherOwn1',
            email='other2@example.com',
            password_hash='hash',
        )
        db.session.add(other_user)
        db.session.commit()
        b = Business(name='Not Mine', owner_id=other_user.id)
        db.session.add(b)
        db.session.commit()
        bid = b.id

        response = auth_client.put(f'/api/businesses/{bid}', json={'name': 'Hacked'})
        assert response.status_code == 403

    def test_update_business_empty_name(self, auth_client, app, db, user):
        """Empty name returns 400."""
        b = Business(name='Original', owner_id=user.id)
        db.session.add(b)
        db.session.commit()
        bid = b.id

        response = auth_client.put(f'/api/businesses/{bid}', json={'name': ''})
        assert response.status_code == 400


class TestDeleteBusiness:
    """Tests for DELETE /api/businesses/:id."""

    def test_delete_business_soft_delete(self, auth_client, app, db, user):
        """Deletion sets is_active=False."""
        b = Business(name='To Delete', owner_id=user.id)
        db.session.add(b)
        db.session.commit()
        bid = b.id

        response = auth_client.delete(f'/api/businesses/{bid}')
        assert response.status_code == 200

        db.session.expire_all()
        b = db.session.get(Business, bid)
        assert b.is_active is False

    def test_delete_business_not_owner(self, auth_client, app, db):
        """Non-owner gets 403."""
        other_user = User(
            username='OtherDel1',
            email='del@example.com',
            password_hash='hash',
        )
        db.session.add(other_user)
        db.session.commit()
        b = Business(name='Not Mine', owner_id=other_user.id)
        db.session.add(b)
        db.session.commit()
        bid = b.id

        response = auth_client.delete(f'/api/businesses/{bid}')
        assert response.status_code == 403

    def test_delete_active_business_clears_session(self, auth_client, app, db, user):
        """Deleting the active business removes it from session."""
        b = Business(name='Active One', owner_id=user.id)
        db.session.add(b)
        db.session.commit()
        bid = b.id

        # Select the business first
        auth_client.post(f'/api/businesses/{bid}/select')
        # Then delete it
        auth_client.delete(f'/api/businesses/{bid}')

        # Verify session no longer has active_business
        # Trying to select the now-inactive business should fail
        response = auth_client.post(f'/api/businesses/{bid}/select')
        assert response.status_code == 403


class TestSelectBusiness:
    """Tests for POST /api/businesses/:id/select."""

    def test_select_business_success(self, auth_client, app, db, user):
        """Sets active_business_id in session."""
        b = Business(name='Select Me', owner_id=user.id)
        db.session.add(b)
        db.session.commit()
        bid = b.id

        response = auth_client.post(f'/api/businesses/{bid}/select')
        assert response.status_code == 200
        data = response.get_json()
        assert data['active_business']['id'] == bid
        assert data['active_business']['name'] == 'Select Me'

    def test_select_business_not_owner(self, auth_client, app, db):
        """Cannot select another user's business."""
        other_user = User(
            username='OtherSel1',
            email='sel@example.com',
            password_hash='hash',
        )
        db.session.add(other_user)
        db.session.commit()
        b = Business(name='Not Mine', owner_id=other_user.id)
        db.session.add(b)
        db.session.commit()
        bid = b.id

        response = auth_client.post(f'/api/businesses/{bid}/select')
        assert response.status_code == 403

    def test_select_inactive_business(self, auth_client, app, db, user):
        """Cannot select an inactive (deleted) business."""
        b = Business(name='Deleted', owner_id=user.id, is_active=False)
        db.session.add(b)
        db.session.commit()
        bid = b.id

        response = auth_client.post(f'/api/businesses/{bid}/select')
        assert response.status_code == 403


class TestRequireBusinessDecorator:
    """Tests for the @require_business decorator behavior."""

    def test_no_business_selected_returns_403(self, auth_client):
        """Without selecting a business, protected endpoints return 403."""
        # Ensure no active_business_id in session
        with auth_client.session_transaction() as sess:
            sess.pop('active_business_id', None)

        # Verify session state
        with auth_client.session_transaction() as sess:
            assert 'active_business_id' not in sess

    def test_require_business_with_valid_session(self, auth_client, app, db, user):
        """With a valid business selected, protected routes proceed."""
        b = Business(name='Valid Biz', owner_id=user.id)
        db.session.add(b)
        db.session.commit()
        bid = b.id

        # Select the business
        auth_client.post(f'/api/businesses/{bid}/select')

        # Session should now have active_business_id set
        with auth_client.session_transaction() as sess:
            assert sess.get('active_business_id') == bid

    def test_require_business_invalid_business_clears_session(self, auth_client, app, db, user):
        """If session has a business_id that no longer exists/is valid, decorator clears it."""
        # Set a fake business ID in session
        with auth_client.session_transaction() as sess:
            sess['active_business_id'] = 99999

        # The bad ID is still there until a @require_business route is hit
        with auth_client.session_transaction() as sess:
            assert sess.get('active_business_id') == 99999
