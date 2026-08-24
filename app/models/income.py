"""Income model."""
from datetime import datetime, timezone
from app import db


class DailyIncome(db.Model):
    """Daily gross income record."""
    __tablename__ = 'daily_incomes'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)  # 0.01 - 999,999,999.99
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('business_id', 'date', name='uq_business_date'),
    )

    def __repr__(self):
        return f'<DailyIncome {self.date}: {self.amount}>'
