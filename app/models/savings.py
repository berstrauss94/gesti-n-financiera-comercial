"""Modelo de asignación de ahorros (fondo de emergencia e inversión).

A diferencia de los gastos, un ahorro es dinero que el usuario APARTA. En el
semáforo se trata con lógica invertida: cuanto mayor sea el porcentaje del
ingreso que se destina a ahorro, mejor (más verde).
"""
from datetime import datetime, timezone

from app import db

# Tipos de ahorro soportados
SAVINGS_EMERGENCY = 'emergencia'
SAVINGS_INVESTMENT = 'inversion'
VALID_SAVINGS_KINDS = (SAVINGS_EMERGENCY, SAVINGS_INVESTMENT)


class SavingsAllocation(db.Model):
    """Aporte a un fondo de ahorro (emergencia o inversión) en una fecha."""
    __tablename__ = 'savings_allocations'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    kind = db.Column(db.String(20), nullable=False)  # emergencia | inversion
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<SavingsAllocation {self.kind} {self.date}: {self.amount}>'
