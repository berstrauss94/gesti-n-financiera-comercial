"""Owner withdrawal model."""
from datetime import datetime, timezone
from app import db


class OwnerWithdrawal(db.Model):
    """Owner personal withdrawals - separate from employee salaries."""
    __tablename__ = 'owner_withdrawals'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<OwnerWithdrawal {self.date}: {self.amount}>'
