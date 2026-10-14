"""Rutas de catálogo de categorías y gestión de categorías activas por negocio.

- GET  /api/catalog                      -> catálogo completo (perfiles + categorías)
- GET  /api/categories                   -> categorías activas del negocio activo + disponibles para agregar
- POST /api/categories                   -> activar una categoría extra (concepto) en el negocio
- DELETE /api/categories/<category>      -> desactivar una categoría del negocio

"Activar" una categoría = crear su ThresholdConfig para el negocio (con los
umbrales por defecto del catálogo). "Desactivar" = borrar ese ThresholdConfig.
"""
from flask import Blueprint, jsonify, request, session

from app import db
from app.catalog import (
    CATEGORIES,
    NET_PROFIT_KEY,
    catalog_payload,
    category_group,
    category_label,
)
from app.models.threshold_config import ThresholdConfig
from app.routes.business import require_business

categories_bp = Blueprint('categories', __name__)


@categories_bp.route('/catalog', methods=['GET'])
@require_business
def get_catalog():
    """Devuelve el catálogo completo de perfiles y categorías."""
    return jsonify(catalog_payload()), 200


@categories_bp.route('/categories', methods=['GET'])
@require_business
def list_active_categories():
    """Lista las categorías activas del negocio y las disponibles para agregar."""
    business_id = session.get('active_business_id')

    rows = ThresholdConfig.query.filter_by(business_id=business_id).all()
    active_keys = {r.category for r in rows if r.category != NET_PROFIT_KEY}

    active = [
        {
            'key': key,
            'label': category_label(key),
            'group': category_group(key),
        }
        for key in CATEGORIES
        if key in active_keys
    ]
    available = [
        {
            'key': key,
            'label': category_label(key),
            'group': category_group(key),
        }
        for key in CATEGORIES
        if key not in active_keys
    ]

    return jsonify({'active': active, 'available': available}), 200


@categories_bp.route('/categories', methods=['POST'])
@require_business
def add_category():
    """Activa una categoría extra (concepto) para el negocio activo.

    Request body: {"category": "comisiones"}
    """
    business_id = session.get('active_business_id')
    data = request.get_json(silent=True) or {}
    category = (data.get('category') or '').strip()

    if category not in CATEGORIES:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_CATEGORY',
                'message': 'Categoría no válida',
                'field': 'category',
            }
        }), 400

    existing = ThresholdConfig.query.filter_by(
        business_id=business_id, category=category
    ).first()
    if existing:
        return jsonify({
            'message': 'La categoría ya estaba activa',
            'category': category,
        }), 200

    green, yellow, orange, red = CATEGORIES[category]['thresholds']
    config = ThresholdConfig(
        business_id=business_id,
        category=category,
        green_max=green,
        yellow_max=yellow,
        orange_max=orange,
        red_max=red,
        is_custom=False,
    )
    db.session.add(config)
    db.session.commit()

    return jsonify({
        'message': 'Categoría agregada',
        'category': {
            'key': category,
            'label': category_label(category),
            'group': category_group(category),
        },
    }), 201


@categories_bp.route('/categories/<category>', methods=['DELETE'])
@require_business
def remove_category(category):
    """Desactiva una categoría del negocio activo (borra su ThresholdConfig)."""
    business_id = session.get('active_business_id')

    if category == NET_PROFIT_KEY:
        return jsonify({
            'error': {
                'code': 'VALIDATION_INVALID_CATEGORY',
                'message': 'La ganancia neta no se puede desactivar',
                'field': 'category',
            }
        }), 400

    config = ThresholdConfig.query.filter_by(
        business_id=business_id, category=category
    ).first()
    if config is None:
        return jsonify({
            'error': {
                'code': 'CATEGORY_NOT_FOUND',
                'message': 'La categoría no estaba activa en este negocio',
            }
        }), 404

    db.session.delete(config)
    db.session.commit()

    return jsonify({'message': 'Categoría desactivada', 'category': category}), 200
