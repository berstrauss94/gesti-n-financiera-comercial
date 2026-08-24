"""Business model for multi-tenant support."""
from datetime import datetime, timezone
from app import db


class Business(db.Model):
    """Business entity - each user can have multiple businesses."""
    __tablename__ = 'businesses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    incomes = db.relationship('DailyIncome', backref='business', lazy='dynamic')
    expenses = db.relationship('Expense', backref='business', lazy='dynamic')

    def __repr__(self):
        return f'<Business {self.name}>'
