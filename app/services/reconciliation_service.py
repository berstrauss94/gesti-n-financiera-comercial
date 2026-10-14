"""Servicio de conciliación bancaria inteligente (REQ-1.1.2).

Cruza las transacciones bancarias importadas (`BankTransaction`) contra los
movimientos registrados en el ERP (gastos e ingresos), emparejando por **monto**
y **fecha** dentro de una tolerancia configurable de días.

Las transacciones con importe negativo se consideran egresos y se intentan
conciliar contra gastos (VariableExpense, OperatingCost, Salary, OwnerWithdrawal);
las de importe positivo se consideran ingresos y se concilian contra DailyIncome.
"""
from datetime import timedelta
from decimal import Decimal

from app import db
from app.models.enterprise import BankAccount, BankTransaction
from app.models.expense import OperatingCost, Salary, VariableExpense
from app.models.income import DailyIncome
from app.models.owner_withdrawal import OwnerWithdrawal

# Tolerancia por defecto para el cruce de fechas (en días)
DEFAULT_DATE_TOLERANCE_DAYS = 2

# Modelos de egreso candidatos: (modelo, campo_fecha)
_EXPENSE_SOURCES = (
    (VariableExpense, 'date'),
    (OperatingCost, 'month'),
    (OwnerWithdrawal, 'date'),
    (Salary, 'period_start'),
)


def _amounts_match(bank_amount, record_amount):
    """Compara importes en valor absoluto con precisión de centavos."""
    return abs(Decimal(str(bank_amount)).copy_abs() - Decimal(str(record_amount)).copy_abs()) <= Decimal('0.01')


def _dates_match(bank_date, record_date, tolerance_days):
    """Verifica que dos fechas estén dentro de la tolerancia indicada."""
    if bank_date is None or record_date is None:
        return False
    delta = abs((bank_date - record_date).days)
    return delta <= tolerance_days


def _find_matching_expense(business_id, tx, tolerance_days):
    """Busca el primer gasto que coincida en monto y fecha con la transacción."""
    tx_date = tx.date.date() if hasattr(tx.date, 'date') else tx.date

    for model, date_field in _EXPENSE_SOURCES:
        candidates = model.query.filter_by(business_id=business_id).all()
        for record in candidates:
            record_date = getattr(record, date_field)
            if _amounts_match(tx.amount, record.amount) and _dates_match(
                tx_date, record_date, tolerance_days
            ):
                return model.__name__, record
    return None, None


def _find_matching_income(business_id, tx, tolerance_days):
    """Busca un ingreso diario que coincida en monto y fecha con la transacción."""
    tx_date = tx.date.date() if hasattr(tx.date, 'date') else tx.date

    incomes = DailyIncome.query.filter_by(business_id=business_id).all()
    for record in incomes:
        if _amounts_match(tx.amount, record.amount) and _dates_match(
            tx_date, record.date, tolerance_days
        ):
            return 'DailyIncome', record
    return None, None


def reconcile_account(account_id, tolerance_days=DEFAULT_DATE_TOLERANCE_DAYS):
    """Concilia todas las transacciones no conciliadas de una cuenta bancaria.

    Args:
        account_id: ID de la BankAccount a conciliar.
        tolerance_days: tolerancia de días para el cruce de fechas.

    Returns:
        dict con resumen de la conciliación.
    """
    account = BankAccount.query.get(account_id)
    if account is None:
        return {'status': 'error', 'message': 'Cuenta bancaria no encontrada'}

    business_id = account.business_id
    pending = BankTransaction.query.filter_by(
        account_id=account_id, reconciled=False
    ).all()

    matched = []
    unmatched = []

    for tx in pending:
        amount = Decimal(str(tx.amount))

        if amount < 0:
            source, record = _find_matching_expense(business_id, tx, tolerance_days)
        else:
            source, record = _find_matching_income(business_id, tx, tolerance_days)

        if record is not None:
            tx.reconciled = True
            tx.reconciled_expense_id = record.id
            matched.append({
                'transaction_id': tx.id,
                'matched_source': source,
                'matched_record_id': record.id,
                'amount': float(tx.amount),
            })
        else:
            unmatched.append({
                'transaction_id': tx.id,
                'amount': float(tx.amount),
                'description': tx.description,
            })

    db.session.commit()

    return {
        'status': 'success',
        'account_id': account_id,
        'processed': len(pending),
        'matched_count': len(matched),
        'unmatched_count': len(unmatched),
        'matched': matched,
        'unmatched': unmatched,
    }
