"""Servicio de OCR para ingesta de documentos de gasto (REQ-1.1.3).

Procesa un `DocumentOCR` (PDF/imagen), extrae monto, proveedor, fecha y
categoría, y registra automáticamente el gasto en `VariableExpense`
(o `OperatingCost` si la categoría pertenece a costos operativos).

NOTA: La extracción OCR real (p.ej. Tesseract / un proveedor cloud) no está
integrada todavía. `_run_ocr` es un punto de extensión: hoy toma los datos ya
extraídos del propio registro `DocumentOCR` o del payload provisto, de modo que
el flujo de impacto contable queda funcional y testeable sin dependencias
externas. Sustituir `_run_ocr` por el motor OCR real cuando esté disponible.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app import db
from app.models.enterprise import DocumentOCR
from app.models.expense import OperatingCost, VariableExpense
from app.schemas import (
    VALID_OPERATING_COST_CATEGORIES,
    VALID_VARIABLE_EXPENSE_CATEGORIES,
)

# Categoría por defecto cuando el OCR no logra clasificar el gasto
DEFAULT_VARIABLE_CATEGORY = 'servicios'


def _coerce_amount(value):
    """Convierte un valor a Decimal(12,2) o devuelve None si no es válido."""
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _coerce_date(value):
    """Convierte un valor a date; acepta date, datetime o 'YYYY-MM-DD'."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def _run_ocr(document, override=None):
    """Punto de extensión para el motor OCR real.

    Hoy devuelve los campos ya extraídos del registro `DocumentOCR`, permitiendo
    sobrescribirlos con `override` (útil para tests o reproceso manual).

    Returns:
        dict con amount, vendor, date_value, category, raw.
    """
    override = override or {}
    return {
        'amount': override.get('amount', document.extracted_amount),
        'vendor': override.get('vendor', document.extracted_vendor),
        'date_value': override.get('date', document.extracted_date),
        'category': override.get('category'),
        'raw': override.get('raw', document.raw_ocr_json),
    }


def _resolve_category(category):
    """Determina el modelo destino según la categoría extraída.

    Returns:
        ('operating', category) | ('variable', category)
    """
    if category in VALID_OPERATING_COST_CATEGORIES:
        return 'operating', category
    if category in VALID_VARIABLE_EXPENSE_CATEGORIES:
        return 'variable', category
    # Fallback: gasto variable con categoría por defecto
    return 'variable', DEFAULT_VARIABLE_CATEGORY


def process_document(document_id, override=None):
    """Procesa un DocumentOCR y registra el gasto correspondiente.

    Args:
        document_id: ID del DocumentOCR a procesar.
        override: dict opcional para forzar valores extraídos
                  (amount, vendor, date, category, raw).

    Returns:
        dict con el resultado del procesamiento.
    """
    document = DocumentOCR.query.get(document_id)
    if document is None:
        return {'status': 'error', 'message': 'Documento no encontrado'}

    extracted = _run_ocr(document, override)

    amount = _coerce_amount(extracted['amount'])
    expense_date = _coerce_date(extracted['date_value']) or date.today()
    vendor = extracted['vendor']

    if amount is None or amount <= 0:
        document.status = 'FAILED'
        if extracted['raw'] is not None:
            document.raw_ocr_json = extracted['raw']
        db.session.commit()
        return {
            'status': 'failed',
            'document_id': document.id,
            'message': 'OCR no pudo extraer un monto válido',
        }

    model_kind, category = _resolve_category(extracted['category'])
    description = f'OCR: {vendor}' if vendor else 'Gasto importado por OCR'

    if model_kind == 'operating':
        # Los costos operativos se agrupan por mes (primer día del mes)
        record = OperatingCost(
            business_id=document.business_id,
            category=category,
            amount=amount,
            month=expense_date.replace(day=1),
            description=description,
        )
    else:
        record = VariableExpense(
            business_id=document.business_id,
            category=category,
            amount=amount,
            date=expense_date,
            description=description,
        )

    db.session.add(record)

    # Actualiza el documento con lo extraído y marca como procesado
    document.status = 'PROCESSED'
    document.extracted_amount = amount
    document.extracted_vendor = vendor
    document.extracted_date = expense_date
    if extracted['raw'] is not None:
        document.raw_ocr_json = extracted['raw']

    db.session.commit()

    return {
        'status': 'success',
        'document_id': document.id,
        'expense_type': model_kind,
        'expense_id': record.id,
        'category': category,
        'amount': float(amount),
        'date': expense_date.isoformat(),
        'vendor': vendor,
    }
