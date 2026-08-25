"""ML Prediction model."""
from datetime import datetime, timezone
from app import db


class MLPrediction(db.Model):
    """Machine Learning prediction record for a business category."""
    __tablename__ = 'ml_predictions'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    predicted_value = db.Column(db.Numeric(12, 2), nullable=False)
    confidence_lower = db.Column(db.Numeric(12, 2), nullable=False)
    confidence_upper = db.Column(db.Numeric(12, 2), nullable=False)
    prediction_date = db.Column(db.Date, nullable=False)
    target_date = db.Column(db.Date, nullable=False)
    recalibrated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<MLPrediction {self.category} -> {self.target_date}: {self.predicted_value}>'
