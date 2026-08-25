"""Tests for ThresholdConfig model and seed_default_thresholds."""
import pytest
from decimal import Decimal
from app.models.threshold_config import (
    ThresholdConfig,
    seed_default_thresholds,
    DEFAULT_THRESHOLDS,
    VALID_THRESHOLD_CATEGORIES,
)
from app.models.business import Business
from app.models.user import User


class TestThresholdConfigModel:
    """Tests for the ThresholdConfig model."""

    def test_create_threshold_config(self, db):
        """Test creating a single ThresholdConfig record."""
        user = User(username='TestUser1', email='test@example.com', password_hash='hash')
        db.session.add(user)
        db.session.flush()

        business = Business(name='Test Business', owner_id=user.id)
        db.session.add(business)
        db.session.flush()

        config = ThresholdConfig(
            business_id=business.id,
            category='salarios',
            green_max=Decimal('18.00'),
            yellow_max=Decimal('22.00'),
            orange_max=Decimal('28.00'),
            red_max=Decimal('35.00'),
            is_custom=False,
        )
        db.session.add(config)
        db.session.commit()

        saved = ThresholdConfig.query.filter_by(business_id=business.id, category='salarios').first()
        assert saved is not None
        assert saved.green_max == Decimal('18.00')
        assert saved.yellow_max == Decimal('22.00')
        assert saved.orange_max == Decimal('28.00')
        assert saved.red_max == Decimal('35.00')
        assert saved.is_custom is False

    def test_unique_constraint_business_category(self, db):
        """Test that UniqueConstraint prevents duplicate (business_id, category)."""
        user = User(username='TestUser2', email='test2@example.com', password_hash='hash')
        db.session.add(user)
        db.session.flush()

        business = Business(name='Test Business', owner_id=user.id)
        db.session.add(business)
        db.session.flush()

        config1 = ThresholdConfig(
            business_id=business.id,
            category='salarios',
            green_max=Decimal('18.00'),
            yellow_max=Decimal('22.00'),
            orange_max=Decimal('28.00'),
            red_max=Decimal('35.00'),
        )
        db.session.add(config1)
        db.session.commit()

        config2 = ThresholdConfig(
            business_id=business.id,
            category='salarios',
            green_max=Decimal('20.00'),
            yellow_max=Decimal('25.00'),
            orange_max=Decimal('30.00'),
            red_max=Decimal('40.00'),
        )
        db.session.add(config2)
        with pytest.raises(Exception):
            db.session.commit()

    def test_same_category_different_business_allowed(self, db):
        """Test that same category is allowed for different businesses."""
        user = User(username='TestUser3', email='test3@example.com', password_hash='hash')
        db.session.add(user)
        db.session.flush()

        biz1 = Business(name='Business 1', owner_id=user.id)
        biz2 = Business(name='Business 2', owner_id=user.id)
        db.session.add_all([biz1, biz2])
        db.session.flush()

        config1 = ThresholdConfig(
            business_id=biz1.id,
            category='salarios',
            green_max=Decimal('18.00'),
            yellow_max=Decimal('22.00'),
            orange_max=Decimal('28.00'),
            red_max=Decimal('35.00'),
        )
        config2 = ThresholdConfig(
            business_id=biz2.id,
            category='salarios',
            green_max=Decimal('18.00'),
            yellow_max=Decimal('22.00'),
            orange_max=Decimal('28.00'),
            red_max=Decimal('35.00'),
        )
        db.session.add_all([config1, config2])
        db.session.commit()

        assert ThresholdConfig.query.count() == 2


class TestSeedDefaultThresholds:
    """Tests for the seed_default_thresholds function."""

    def test_seed_creates_all_categories(self, db):
        """Test that seeding creates one config per category."""
        user = User(username='TestUser4', email='test4@example.com', password_hash='hash')
        db.session.add(user)
        db.session.flush()

        business = Business(name='Test Business', owner_id=user.id)
        db.session.add(business)
        db.session.commit()

        created = seed_default_thresholds(business.id)

        assert len(created) == len(DEFAULT_THRESHOLDS)
        assert ThresholdConfig.query.filter_by(business_id=business.id).count() == len(DEFAULT_THRESHOLDS)

    def test_seed_uses_correct_defaults(self, db):
        """Test that seeded configs have the correct default values."""
        user = User(username='TestUser5', email='test5@example.com', password_hash='hash')
        db.session.add(user)
        db.session.flush()

        business = Business(name='Test Business', owner_id=user.id)
        db.session.add(business)
        db.session.commit()

        seed_default_thresholds(business.id)

        salarios = ThresholdConfig.query.filter_by(
            business_id=business.id, category='salarios'
        ).first()
        assert salarios.green_max == Decimal('18.00')
        assert salarios.yellow_max == Decimal('22.00')
        assert salarios.orange_max == Decimal('28.00')
        assert salarios.red_max == Decimal('35.00')

        retiros = ThresholdConfig.query.filter_by(
            business_id=business.id, category='retiros_dueno'
        ).first()
        assert retiros.green_max == Decimal('10.00')
        assert retiros.yellow_max == Decimal('15.00')
        assert retiros.orange_max == Decimal('20.00')
        assert retiros.red_max == Decimal('25.00')

        mercaderia = ThresholdConfig.query.filter_by(
            business_id=business.id, category='mercaderia'
        ).first()
        assert mercaderia.green_max == Decimal('40.00')
        assert mercaderia.yellow_max == Decimal('45.00')
        assert mercaderia.orange_max == Decimal('50.00')
        assert mercaderia.red_max == Decimal('60.00')

    def test_seed_marks_as_not_custom(self, db):
        """Test that all seeded configs have is_custom=False."""
        user = User(username='TestUser6', email='test6@example.com', password_hash='hash')
        db.session.add(user)
        db.session.flush()

        business = Business(name='Test Business', owner_id=user.id)
        db.session.add(business)
        db.session.commit()

        seed_default_thresholds(business.id)

        configs = ThresholdConfig.query.filter_by(business_id=business.id).all()
        for config in configs:
            assert config.is_custom is False

    def test_seed_is_idempotent(self, db):
        """Test that calling seed twice does not create duplicates."""
        user = User(username='TestUser7', email='test7@example.com', password_hash='hash')
        db.session.add(user)
        db.session.flush()

        business = Business(name='Test Business', owner_id=user.id)
        db.session.add(business)
        db.session.commit()

        first_run = seed_default_thresholds(business.id)
        second_run = seed_default_thresholds(business.id)

        assert len(first_run) == len(DEFAULT_THRESHOLDS)
        assert len(second_run) == 0
        assert ThresholdConfig.query.filter_by(business_id=business.id).count() == len(DEFAULT_THRESHOLDS)

    def test_all_valid_categories_have_defaults(self):
        """Test that every valid category has a default threshold defined."""
        for category in VALID_THRESHOLD_CATEGORIES:
            assert category in DEFAULT_THRESHOLDS, f"Missing default for category: {category}"
