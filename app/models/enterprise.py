"""Enterprise feature models.

Modelos para módulos Enterprise: sincronización bancaria, OCR, catálogo/WMS,
MRP, campos dinámicos (Studio), firma digital y helpdesk.

Todos los modelos de nivel superior llevan `business_id` para garantizar el
aislamiento multi-tenant nativo del sistema base.
"""
from datetime import datetime, timezone

from sqlalchemy import JSON

from app import db


def _utcnow():
    """Return a timezone-aware UTC timestamp (consistente con el resto de modelos)."""
    return datetime.now(timezone.utc)


# --- 1.1 Inteligencia Financiera y Automatización Contable ---

class BankAccount(db.Model):
    """Cuenta bancaria vinculada a un negocio (REQ-1.1.1)."""
    __tablename__ = 'bank_accounts'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    currency = db.Column(db.String(3), default='ARS')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=_utcnow)

    transactions = db.relationship(
        'BankTransaction',
        backref='account',
        lazy=True,
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<BankAccount {self.bank_name} ({self.account_number})>'


class BankTransaction(db.Model):
    """Movimiento bancario importado desde un extracto (REQ-1.1.2)."""
    __tablename__ = 'bank_transactions'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=_utcnow)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.String(255))
    # fitid: identificador único del movimiento en formatos OFX/extractos (evita duplicados)
    fitid = db.Column(db.String(100), unique=True)
    reconciled = db.Column(db.Boolean, default=False)
    reconciled_expense_id = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f'<BankTransaction {self.amount} on {self.date}>'


class DocumentOCR(db.Model):
    """Documento ingerido para extracción OCR de datos de gasto (REQ-1.1.3)."""
    __tablename__ = 'document_ocrs'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='PENDING')  # PENDING, PROCESSED, FAILED
    raw_ocr_json = db.Column(JSON, nullable=True)
    extracted_amount = db.Column(db.Numeric(12, 2), nullable=True)
    extracted_vendor = db.Column(db.String(100), nullable=True)
    extracted_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow)

    def __repr__(self):
        return f'<DocumentOCR {self.file_path} [{self.status}]>'


# --- 1.2 Control de Operaciones y Logística (WMS / MRP) ---

class Product(db.Model):
    """Producto del catálogo con soporte para código de barras (REQ-1.2.1)."""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    sku = db.Column(db.String(50), index=True)
    barcode = db.Column(db.String(100), index=True)
    name = db.Column(db.String(150), nullable=False)
    cost_price = db.Column(db.Numeric(12, 2), default=0)
    sale_price = db.Column(db.Numeric(12, 2), default=0)
    stock_quantity = db.Column(db.Numeric(12, 3), default=0)
    created_at = db.Column(db.DateTime, default=_utcnow)

    def __repr__(self):
        return f'<Product {self.sku} - {self.name}>'


class ProductionOrder(db.Model):
    """Orden de producción (MRP) con control de calidad (REQ-1.2.2)."""
    __tablename__ = 'production_orders'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    status = db.Column(db.String(20), default='DRAFT')  # DRAFT, IN_PROGRESS, DONE, CANCELLED
    quality_check_passed = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=_utcnow)

    def __repr__(self):
        return f'<ProductionOrder #{self.id} [{self.status}]>'


# --- 1.3 Personalización y Campos Dinámicos (Studio / Low-Code) ---

class CustomField(db.Model):
    """Definición de un campo personalizado para una entidad (REQ-1.3.1)."""
    __tablename__ = 'custom_fields'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    target_model = db.Column(db.String(50), nullable=False)
    field_name = db.Column(db.String(50), nullable=False)
    field_label = db.Column(db.String(100), nullable=False)
    field_type = db.Column(db.String(20), nullable=False)  # string, number, boolean, date

    def __repr__(self):
        return f'<CustomField {self.target_model}.{self.field_name}>'


class CustomFieldValue(db.Model):
    """Valor desacoplado (JSON) de un campo personalizado para un registro (REQ-1.3.2)."""
    __tablename__ = 'custom_field_values'

    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey('custom_fields.id'), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    value_json = db.Column(JSON, nullable=False)

    def __repr__(self):
        return f'<CustomFieldValue field={self.field_id} record={self.record_id}>'


# --- 1.4 Productividad y Servicios ---

class DigitalSignature(db.Model):
    """Firma electrónica con trazabilidad y hash de auditoría (REQ-1.4.1)."""
    __tablename__ = 'digital_signatures'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    document_title = db.Column(db.String(150), nullable=False)
    signer_email = db.Column(db.String(120), nullable=False)
    signature_hash = db.Column(db.String(256), nullable=True)
    status = db.Column(db.String(20), default='PENDING')  # PENDING, SIGNED, REJECTED
    signed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow)

    def __repr__(self):
        return f'<DigitalSignature {self.document_title} [{self.status}]>'


class HelpdeskTicket(db.Model):
    """Ticket de soporte asignado a un negocio con prioridad y SLA (REQ-1.4.2)."""
    __tablename__ = 'helpdesk_tickets'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    priority = db.Column(db.String(10), default='MEDIUM')  # LOW, MEDIUM, HIGH, URGENT
    status = db.Column(db.String(20), default='NEW')  # NEW, OPEN, PENDING, RESOLVED, CLOSED
    sla_deadline = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow)

    def __repr__(self):
        return f'<HelpdeskTicket #{self.id} [{self.priority}/{self.status}]>'
