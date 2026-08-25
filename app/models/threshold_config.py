"""Threshold configuration model for heatmap color mapping."""
from datetime import datetime, timezone
from decimal import Decimal
from app import db


# Valid categories for threshold configuration
VALID_THRESHOLD_CATEGORIES = [
    'salarios',
    'retiros_dueno',
    'mercaderia',
    # 8 variable expense categories
    'comisiones',
    'mermas',
    'servicios',
    'insumos',
    'mantenimiento',
    'impuestos_municipales',
    'seguros',
    'logistica',
    # Operating costs
    'electricidad',
    'monotributo',
    'alquiler',
    'contable',
    # Net profit (inverted logic - higher is better)
    'ganancia_neta',
]

# Default thresholds: (green_max, yellow_max, orange_max, red_max)
# For expenses: below green_max is green, above red_max is critical
# For ganancia_neta: inverted (>=20 green, 10-20 yellow, 5-10 orange, <5 red)
DEFAULT_THRESHOLDS = {
    'salarios': (Decimal('18.00'), Decimal('22.00'), Decimal('28.00'), Decimal('35.00')),
    'retiros_dueno': (Decimal('10.00'), Decimal('15.00'), Decimal('20.00'), Decimal('25.00')),
    'mercaderia': (Decimal('40.00'), Decimal('45.00'), Decimal('50.00'), Decimal('60.00')),
    # Variable expenses - reasonable defaults for small businesses
    'comisiones': (Decimal('3.00'), Decimal('5.00'), Decimal('7.00'), Decimal('10.00')),
    'mermas': (Decimal('2.00'), Decimal('4.00'), Decimal('6.00'), Decimal('8.00')),
    'servicios': (Decimal('3.00'), Decimal('5.00'), Decimal('7.00'), Decimal('10.00')),
    'insumos': (Decimal('5.00'), Decimal('8.00'), Decimal('12.00'), Decimal('15.00')),
    'mantenimiento': (Decimal('3.00'), Decimal('5.00'), Decimal('8.00'), Decimal('10.00')),
    'impuestos_municipales': (Decimal('2.00'), Decimal('4.00'), Decimal('6.00'), Decimal('8.00')),
    'seguros': (Decimal('2.00'), Decimal('4.00'), Decimal('6.00'), Decimal('8.00')),
    'logistica': (Decimal('3.00'), Decimal('5.00'), Decimal('8.00'), Decimal('10.00')),
    # Operating costs
    'electricidad': (Decimal('3.00'), Decimal('5.00'), Decimal('7.00'), Decimal('10.00')),
    'monotributo': (Decimal('5.00'), Decimal('8.00'), Decimal('10.00'), Decimal('15.00')),
    'alquiler': (Decimal('8.00'), Decimal('12.00'), Decimal('15.00'), Decimal('20.00')),
    'contable': (Decimal('2.00'), Decimal('4.00'), Decimal('6.00'), Decimal('8.00')),
    # Net profit (thresholds represent minimums - inverted logic)
    'ganancia_neta': (Decimal('20.00'), Decimal('10.00'), Decimal('5.00'), Decimal('0.00')),
}


class ThresholdConfig(db.Model):
    """Configurable thresholds per category per business."""
    __tablename__ = 'threshold_configs'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    green_max = db.Column(db.Numeric(5, 2), nullable=False)
    yellow_max = db.Column(db.Numeric(5, 2), nullable=False)
    orange_max = db.Column(db.Numeric(5, 2), nullable=False)
    red_max = db.Column(db.Numeric(5, 2), nullable=False)
    is_custom = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('business_id', 'category', name='uq_business_category_threshold'),
    )

    def __repr__(self):
        return f'<ThresholdConfig {self.category} for business {self.business_id}>'


def seed_default_thresholds(business_id):
    """
    Create default threshold configurations for all categories for a given business.

    This function creates one ThresholdConfig entry per category using the
    predefined DEFAULT_THRESHOLDS values. Existing configurations for the
    business are skipped (upsert-safe).

    Args:
        business_id: The ID of the business to seed thresholds for.

    Returns:
        list[ThresholdConfig]: List of created ThresholdConfig instances.
    """
    created = []

    for category, (green_max, yellow_max, orange_max, red_max) in DEFAULT_THRESHOLDS.items():
        # Skip if configuration already exists for this business+category
        existing = ThresholdConfig.query.filter_by(
            business_id=business_id,
            category=category
        ).first()

        if existing is None:
            config = ThresholdConfig(
                business_id=business_id,
                category=category,
                green_max=green_max,
                yellow_max=yellow_max,
                orange_max=orange_max,
                red_max=red_max,
                is_custom=False,
            )
            db.session.add(config)
            created.append(config)

    if created:
        db.session.commit()

    return created
