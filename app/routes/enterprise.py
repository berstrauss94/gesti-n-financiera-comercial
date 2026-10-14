"""Rutas de los módulos Enterprise.

Prefijo: /api/enterprise. Todos los endpoints usan @require_business, que
valida la sesión y el negocio activo. Siguiendo el patrón del resto del
proyecto (ver expenses.py / income.py), el business_id se obtiene desde
session['active_business_id'] dentro de cada handler (el decorador NO lo
inyecta como argumento).
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from app import db
from app.models.enterprise import (
    BankAccount,
    BankTransaction,
    CustomField,
    CustomFieldValue,
    DigitalSignature,
    DocumentOCR,
    HelpdeskTicket,
    Product,
    ProductionOrder,
)
from app.routes.business import require_business
from app.services.ocr_service import process_document
from app.services.reconciliation_service import reconcile_account

enterprise_bp = Blueprint('enterprise', __name__, url_prefix='/api/enterprise')


def _active_business_id():
    """Devuelve el negocio activo validado por require_business."""
    return session.get('active_business_id')


def _bad_request(message, field=None):
    return jsonify({
        'error': {
            'code': 'VALIDATION_INVALID_INPUT',
            'message': message,
            'field': field,
        }
    }), 400


def _parse_datetime(value):
    """Parsea una fecha/hora ISO; devuelve None si no es válida."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


# --- 1.2.1 Catálogo & Barcode (Product) ---

@enterprise_bp.route('/products', methods=['GET', 'POST'])
@require_business
def handle_products():
    business_id = _active_business_id()

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        if not data.get('name'):
            return _bad_request('El nombre del producto es requerido', 'name')

        product = Product(
            business_id=business_id,
            sku=data.get('sku'),
            barcode=data.get('barcode'),
            name=data['name'],
            cost_price=data.get('cost_price', 0),
            sale_price=data.get('sale_price', 0),
            stock_quantity=data.get('stock_quantity', 0),
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({'message': 'Producto creado con éxito', 'id': product.id}), 201

    products = Product.query.filter_by(business_id=business_id).all()
    return jsonify([
        {
            'id': p.id,
            'sku': p.sku,
            'barcode': p.barcode,
            'name': p.name,
            'stock': float(p.stock_quantity),
            'cost_price': float(p.cost_price),
            'sale_price': float(p.sale_price),
        }
        for p in products
    ]), 200


@enterprise_bp.route('/products/barcode/<barcode>', methods=['GET'])
@require_business
def get_by_barcode(barcode):
    business_id = _active_business_id()
    product = Product.query.filter_by(
        business_id=business_id, barcode=barcode
    ).first()
    if not product:
        return jsonify({'error': 'Producto no encontrado'}), 404
    return jsonify({
        'id': product.id,
        'name': product.name,
        'stock': float(product.stock_quantity),
        'sale_price': float(product.sale_price),
    }), 200


# --- 1.2.2 MRP & Calidad (ProductionOrder) ---

_VALID_PRODUCTION_STATUSES = {'DRAFT', 'IN_PROGRESS', 'DONE', 'CANCELLED'}


@enterprise_bp.route('/production-orders', methods=['GET', 'POST'])
@require_business
def handle_production_orders():
    business_id = _active_business_id()

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        product_id = data.get('product_id')
        quantity = data.get('quantity')
        if product_id is None or quantity is None:
            return _bad_request('product_id y quantity son requeridos')

        # El producto debe pertenecer al negocio activo (aislamiento multi-tenant)
        product = Product.query.filter_by(
            id=product_id, business_id=business_id
        ).first()
        if product is None:
            return jsonify({'error': 'Producto no encontrado'}), 404

        order = ProductionOrder(
            business_id=business_id,
            product_id=product_id,
            quantity=quantity,
            status=data.get('status', 'DRAFT'),
            quality_check_passed=data.get('quality_check_passed', True),
        )
        if order.status not in _VALID_PRODUCTION_STATUSES:
            return _bad_request('Estado de orden inválido', 'status')

        db.session.add(order)
        db.session.commit()
        return jsonify({'message': 'Orden de producción creada', 'id': order.id}), 201

    orders = ProductionOrder.query.filter_by(business_id=business_id).all()
    return jsonify([
        {
            'id': o.id,
            'product_id': o.product_id,
            'quantity': float(o.quantity),
            'status': o.status,
            'quality_check_passed': o.quality_check_passed,
        }
        for o in orders
    ]), 200


@enterprise_bp.route('/production-orders/<int:order_id>', methods=['PUT'])
@require_business
def update_production_order(order_id):
    business_id = _active_business_id()
    order = ProductionOrder.query.filter_by(
        id=order_id, business_id=business_id
    ).first()
    if order is None:
        return jsonify({'error': 'Orden no encontrada'}), 404

    data = request.get_json(silent=True) or {}
    if 'status' in data:
        if data['status'] not in _VALID_PRODUCTION_STATUSES:
            return _bad_request('Estado de orden inválido', 'status')
        order.status = data['status']
    if 'quality_check_passed' in data:
        order.quality_check_passed = bool(data['quality_check_passed'])

    db.session.commit()
    return jsonify({
        'id': order.id,
        'status': order.status,
        'quality_check_passed': order.quality_check_passed,
    }), 200


# --- 1.3 Studio: campos dinámicos (CustomField / CustomFieldValue) ---

_VALID_FIELD_TYPES = {'string', 'number', 'boolean', 'date'}


@enterprise_bp.route('/custom-fields', methods=['GET', 'POST'])
@require_business
def handle_custom_fields():
    business_id = _active_business_id()

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        required = ('target_model', 'field_name', 'field_label', 'field_type')
        missing = [k for k in required if not data.get(k)]
        if missing:
            return _bad_request(f'Campos requeridos: {", ".join(missing)}')
        if data['field_type'] not in _VALID_FIELD_TYPES:
            return _bad_request('field_type inválido', 'field_type')

        field = CustomField(
            business_id=business_id,
            target_model=data['target_model'],
            field_name=data['field_name'],
            field_label=data['field_label'],
            field_type=data['field_type'],
        )
        db.session.add(field)
        db.session.commit()
        return jsonify({'message': 'Campo personalizado creado', 'id': field.id}), 201

    target_model = request.args.get('target_model')
    query = CustomField.query.filter_by(business_id=business_id)
    if target_model:
        query = query.filter_by(target_model=target_model)
    fields = query.all()
    return jsonify([
        {
            'id': f.id,
            'target_model': f.target_model,
            'field_name': f.field_name,
            'field_label': f.field_label,
            'field_type': f.field_type,
        }
        for f in fields
    ]), 200


@enterprise_bp.route('/custom-values', methods=['POST'])
@require_business
def set_custom_value():
    business_id = _active_business_id()
    data = request.get_json(silent=True) or {}

    field_id = data.get('field_id')
    record_id = data.get('record_id')
    if field_id is None or record_id is None or 'value' not in data:
        return _bad_request('field_id, record_id y value son requeridos')

    # El campo debe pertenecer al negocio activo
    field = CustomField.query.filter_by(
        id=field_id, business_id=business_id
    ).first()
    if field is None:
        return jsonify({'error': 'Campo personalizado no encontrado'}), 404

    # Upsert: actualiza si ya existe un valor para (field, record)
    existing = CustomFieldValue.query.filter_by(
        field_id=field_id, record_id=record_id
    ).first()
    if existing:
        existing.value_json = data['value']
        db.session.commit()
        return jsonify({'message': 'Valor actualizado', 'id': existing.id}), 200

    value = CustomFieldValue(
        field_id=field_id,
        record_id=record_id,
        value_json=data['value'],
    )
    db.session.add(value)
    db.session.commit()
    return jsonify({'message': 'Valor creado', 'id': value.id}), 201


# --- 1.4.1 Firma digital (DigitalSignature) ---

@enterprise_bp.route('/signatures', methods=['GET', 'POST'])
@require_business
def handle_signatures():
    business_id = _active_business_id()

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        if not data.get('document_title') or not data.get('signer_email'):
            return _bad_request('document_title y signer_email son requeridos')

        signature = DigitalSignature(
            business_id=business_id,
            document_title=data['document_title'],
            signer_email=data['signer_email'],
            status='PENDING',
        )
        db.session.add(signature)
        db.session.commit()
        return jsonify({'message': 'Solicitud de firma creada', 'id': signature.id}), 201

    signatures = DigitalSignature.query.filter_by(business_id=business_id).all()
    return jsonify([
        {
            'id': s.id,
            'document_title': s.document_title,
            'signer_email': s.signer_email,
            'status': s.status,
            'signed_at': s.signed_at.isoformat() if s.signed_at else None,
        }
        for s in signatures
    ]), 200


@enterprise_bp.route('/signatures/<int:signature_id>/sign', methods=['POST'])
@require_business
def sign_document(signature_id):
    import hashlib

    business_id = _active_business_id()
    signature = DigitalSignature.query.filter_by(
        id=signature_id, business_id=business_id
    ).first()
    if signature is None:
        return jsonify({'error': 'Firma no encontrada'}), 404
    if signature.status == 'SIGNED':
        return jsonify({'error': 'El documento ya fue firmado'}), 409

    now = datetime.now(timezone.utc)
    # Hash de auditoría a partir de datos del documento + timestamp
    payload = f'{signature.id}|{signature.document_title}|{signature.signer_email}|{now.isoformat()}'
    signature.signature_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    signature.status = 'SIGNED'
    signature.signed_at = now
    db.session.commit()

    return jsonify({
        'id': signature.id,
        'status': signature.status,
        'signature_hash': signature.signature_hash,
        'signed_at': signature.signed_at.isoformat(),
    }), 200


# --- 1.4.2 Helpdesk & SLA (HelpdeskTicket) ---

@enterprise_bp.route('/tickets', methods=['GET', 'POST'])
@require_business
def handle_tickets():
    business_id = _active_business_id()

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        if not data.get('subject'):
            return _bad_request('El asunto del ticket es requerido', 'subject')

        ticket = HelpdeskTicket(
            business_id=business_id,
            subject=data['subject'],
            priority=data.get('priority', 'MEDIUM'),
            status=data.get('status', 'NEW'),
            sla_deadline=_parse_datetime(data.get('sla_deadline')),
        )
        db.session.add(ticket)
        db.session.commit()
        return jsonify({'message': 'Ticket creado', 'id': ticket.id}), 201

    tickets = HelpdeskTicket.query.filter_by(business_id=business_id).all()
    return jsonify([
        {
            'id': t.id,
            'subject': t.subject,
            'priority': t.priority,
            'status': t.status,
            'sla_deadline': t.sla_deadline.isoformat() if t.sla_deadline else None,
        }
        for t in tickets
    ]), 200


# --- 1.1.1 Cuentas bancarias (BankAccount) ---

@enterprise_bp.route('/bank-accounts', methods=['GET', 'POST'])
@require_business
def handle_bank_accounts():
    business_id = _active_business_id()

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        if not data.get('bank_name') or not data.get('account_number'):
            return _bad_request('bank_name y account_number son requeridos')

        account = BankAccount(
            business_id=business_id,
            bank_name=data['bank_name'],
            account_number=data['account_number'],
            currency=data.get('currency', 'ARS'),
        )
        db.session.add(account)
        db.session.commit()
        return jsonify({'message': 'Cuenta bancaria creada', 'id': account.id}), 201

    accounts = BankAccount.query.filter_by(
        business_id=business_id, is_active=True
    ).all()
    return jsonify([
        {
            'id': a.id,
            'bank_name': a.bank_name,
            'account_number': a.account_number,
            'currency': a.currency,
        }
        for a in accounts
    ]), 200


@enterprise_bp.route('/bank-accounts/<int:account_id>/transactions', methods=['POST'])
@require_business
def import_transactions(account_id):
    """Importa movimientos a una cuenta bancaria (REQ-1.1.1)."""
    business_id = _active_business_id()
    account = BankAccount.query.filter_by(
        id=account_id, business_id=business_id
    ).first()
    if account is None:
        return jsonify({'error': 'Cuenta bancaria no encontrada'}), 404

    data = request.get_json(silent=True) or {}
    items = data.get('transactions')
    if not isinstance(items, list) or not items:
        return _bad_request('Se requiere una lista "transactions" no vacía')

    created = 0
    skipped = 0
    for item in items:
        fitid = item.get('fitid')
        # Evita duplicados por fitid (identificador único del extracto)
        if fitid and BankTransaction.query.filter_by(fitid=fitid).first():
            skipped += 1
            continue
        tx = BankTransaction(
            account_id=account_id,
            date=_parse_datetime(item.get('date')) or datetime.now(timezone.utc),
            amount=item.get('amount', 0),
            description=item.get('description'),
            fitid=fitid,
        )
        db.session.add(tx)
        created += 1

    db.session.commit()
    return jsonify({
        'message': 'Importación completada',
        'created': created,
        'skipped_duplicates': skipped,
    }), 201


@enterprise_bp.route('/bank-accounts/<int:account_id>/reconcile', methods=['POST'])
@require_business
def reconcile(account_id):
    """Ejecuta la conciliación inteligente de una cuenta (REQ-1.1.2)."""
    business_id = _active_business_id()
    account = BankAccount.query.filter_by(
        id=account_id, business_id=business_id
    ).first()
    if account is None:
        return jsonify({'error': 'Cuenta bancaria no encontrada'}), 404

    data = request.get_json(silent=True) or {}
    tolerance = data.get('tolerance_days', 2)
    result = reconcile_account(account_id, tolerance_days=tolerance)
    return jsonify(result), 200


# --- 1.1.3 OCR de documentos (DocumentOCR) ---

@enterprise_bp.route('/documents', methods=['POST'])
@require_business
def create_document():
    """Registra un documento para procesamiento OCR (REQ-1.1.3)."""
    business_id = _active_business_id()
    data = request.get_json(silent=True) or {}
    if not data.get('file_path'):
        return _bad_request('file_path es requerido', 'file_path')

    document = DocumentOCR(
        business_id=business_id,
        file_path=data['file_path'],
        status='PENDING',
    )
    db.session.add(document)
    db.session.commit()
    return jsonify({'message': 'Documento registrado', 'id': document.id}), 201


@enterprise_bp.route('/documents/<int:document_id>/process', methods=['POST'])
@require_business
def process_ocr(document_id):
    """Procesa el OCR de un documento e impacta el gasto automáticamente."""
    business_id = _active_business_id()
    document = DocumentOCR.query.filter_by(
        id=document_id, business_id=business_id
    ).first()
    if document is None:
        return jsonify({'error': 'Documento no encontrado'}), 404

    override = (request.get_json(silent=True) or {}).get('override')
    result = process_document(document_id, override=override)
    status_code = 200 if result.get('status') == 'success' else 422
    return jsonify(result), status_code
