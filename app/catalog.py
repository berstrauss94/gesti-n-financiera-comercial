"""Catálogo central de categorías y perfiles de negocio.

Fuente única de verdad para:
  - Los perfiles de negocio (business_type) disponibles.
  - Las categorías de gasto, con su grupo, etiqueta en español, umbrales por
    defecto y a qué perfiles pertenecen por defecto.

Diseño:
  - Cada categoría pertenece a un GRUPO que define contra qué modelo se guarda
    y cómo se trata: 'variable' (VariableExpense), 'operativo' (OperatingCost),
    'salarios' (Salary) y 'retiros' (OwnerWithdrawal).
  - Cada categoría declara en qué perfiles aparece POR DEFECTO. Un negocio puede
    además activar categorías "extra" opt-in que no son de su perfil (se guardan
    como ThresholdConfig del negocio).
  - El perfil 'comercio' incluye TODAS las categorías actuales, de modo que el
    comportamiento previo del sistema queda intacto (retrocompatibilidad).

Umbrales: tupla (green_max, yellow_max, orange_max, red_max) en % del ingreso.
"""
from decimal import Decimal

# Perfiles de negocio disponibles
BUSINESS_PROFILES = {
    'comercio': {
        'label': 'Comercio / Retail',
        'description': 'Tienda o comercio con empleados, mercadería y costos operativos completos.',
    },
    'hogar': {
        'label': 'Hogar / Finanzas personales',
        'description': 'Gastos de un hogar: alquiler, servicios, supermercado, transporte, salud.',
    },
    'expansion': {
        'label': 'Negocio en expansión / Pyme',
        'description': 'Negocio en crecimiento: set completo con foco en logística e inversión.',
    },
    'servicios': {
        'label': 'Servicios / Profesional independiente',
        'description': 'Prestador de servicios: honorarios, servicios e impuestos, sin mercadería.',
    },
}

DEFAULT_PROFILE = 'comercio'

# Grupos de categoría -> cómo se tratan
GROUP_VARIABLE = 'variable'    # VariableExpense (por fecha)
GROUP_OPERATIVO = 'operativo'  # OperatingCost (por mes)
GROUP_SALARIOS = 'salarios'    # Salary (por período)
GROUP_RETIROS = 'retiros'      # OwnerWithdrawal (por fecha)
GROUP_AHORRO = 'ahorro'        # SavingsAllocation (lógica invertida: más = mejor)

# Catálogo de categorías.
# key -> {label, group, thresholds, profiles}
# "profiles" = perfiles donde la categoría aparece POR DEFECTO.
CATEGORIES = {
    # --- Especiales (siempre presentes salvo que el perfil las excluya) ---
    'salarios': {
        'label': 'Salarios',
        'group': GROUP_SALARIOS,
        'thresholds': (Decimal('18.00'), Decimal('22.00'), Decimal('28.00'), Decimal('35.00')),
        'profiles': {'comercio', 'expansion'},
    },
    'retiros_dueno': {
        'label': 'Retiros del Dueño',
        'group': GROUP_RETIROS,
        'thresholds': (Decimal('10.00'), Decimal('15.00'), Decimal('20.00'), Decimal('25.00')),
        'profiles': {'comercio', 'expansion', 'servicios'},
    },
    # --- Gastos variables ---
    'comisiones': {
        'label': 'Comisiones',
        'group': GROUP_VARIABLE,
        'thresholds': (Decimal('3.00'), Decimal('5.00'), Decimal('7.00'), Decimal('10.00')),
        'profiles': {'comercio', 'expansion', 'servicios'},
    },
    'mermas': {
        'label': 'Mermas',
        'group': GROUP_VARIABLE,
        'thresholds': (Decimal('2.00'), Decimal('4.00'), Decimal('6.00'), Decimal('8.00')),
        'profiles': {'comercio', 'expansion'},
    },
    'servicios': {
        'label': 'Servicios',
        'group': GROUP_VARIABLE,
        'thresholds': (Decimal('3.00'), Decimal('5.00'), Decimal('7.00'), Decimal('10.00')),
        'profiles': {'comercio', 'expansion', 'servicios', 'hogar'},
    },
    'insumos': {
        'label': 'Insumos',
        'group': GROUP_VARIABLE,
        'thresholds': (Decimal('5.00'), Decimal('8.00'), Decimal('12.00'), Decimal('15.00')),
        'profiles': {'comercio', 'expansion', 'servicios'},
    },
    'mantenimiento': {
        'label': 'Mantenimiento',
        'group': GROUP_VARIABLE,
        'thresholds': (Decimal('3.00'), Decimal('5.00'), Decimal('8.00'), Decimal('10.00')),
        'profiles': {'comercio', 'expansion', 'servicios', 'hogar'},
    },
    'impuestos_municipales': {
        'label': 'Impuestos Municipales',
        'group': GROUP_VARIABLE,
        'thresholds': (Decimal('2.00'), Decimal('4.00'), Decimal('6.00'), Decimal('8.00')),
        'profiles': {'comercio', 'expansion', 'servicios', 'hogar'},
    },
    'seguros': {
        'label': 'Seguros',
        'group': GROUP_VARIABLE,
        'thresholds': (Decimal('2.00'), Decimal('4.00'), Decimal('6.00'), Decimal('8.00')),
        'profiles': {'comercio', 'expansion', 'servicios', 'hogar'},
    },
    'logistica': {
        'label': 'Logística',
        'group': GROUP_VARIABLE,
        'thresholds': (Decimal('3.00'), Decimal('5.00'), Decimal('8.00'), Decimal('10.00')),
        'profiles': {'comercio', 'expansion'},
    },
    # --- Costos operativos ---
    'electricidad': {
        'label': 'Electricidad',
        'group': GROUP_OPERATIVO,
        'thresholds': (Decimal('3.00'), Decimal('5.00'), Decimal('7.00'), Decimal('10.00')),
        'profiles': {'comercio', 'expansion', 'servicios', 'hogar'},
    },
    'monotributo': {
        'label': 'Monotributo',
        'group': GROUP_OPERATIVO,
        'thresholds': (Decimal('5.00'), Decimal('8.00'), Decimal('10.00'), Decimal('15.00')),
        'profiles': {'comercio', 'expansion', 'servicios'},
    },
    'mercaderia': {
        'label': 'Mercadería',
        'group': GROUP_OPERATIVO,
        'thresholds': (Decimal('40.00'), Decimal('45.00'), Decimal('50.00'), Decimal('60.00')),
        'profiles': {'comercio', 'expansion', 'hogar'},
    },
    'alquiler': {
        'label': 'Alquiler',
        'group': GROUP_OPERATIVO,
        'thresholds': (Decimal('8.00'), Decimal('12.00'), Decimal('15.00'), Decimal('20.00')),
        'profiles': {'comercio', 'expansion', 'servicios', 'hogar'},
    },
    'contable': {
        'label': 'Contable',
        'group': GROUP_OPERATIVO,
        'thresholds': (Decimal('2.00'), Decimal('4.00'), Decimal('6.00'), Decimal('8.00')),
        'profiles': {'comercio', 'expansion', 'servicios'},
    },
    'agua': {
        'label': 'Agua',
        'group': GROUP_OPERATIVO,
        'thresholds': (Decimal('2.00'), Decimal('3.00'), Decimal('5.00'), Decimal('7.00')),
        'profiles': {'comercio', 'expansion', 'servicios', 'hogar'},
    },
    'internet': {
        'label': 'Internet',
        'group': GROUP_OPERATIVO,
        'thresholds': (Decimal('2.00'), Decimal('3.00'), Decimal('5.00'), Decimal('7.00')),
        'profiles': {'comercio', 'expansion', 'servicios', 'hogar'},
    },
    # --- Ahorros (lógica invertida: más % del ingreso es mejor) ---
    # Umbrales (green_min, yellow_min, orange_min) en % del ingreso. Ver nota abajo.
    'emergencia': {
        'label': 'Fondo de Emergencia',
        'group': GROUP_AHORRO,
        'inverted': True,
        # verde >=10%, amarillo >=5%, naranja >=2%, rojo <2%
        'thresholds': (Decimal('10.00'), Decimal('5.00'), Decimal('2.00'), Decimal('0.00')),
        'profiles': {'comercio', 'expansion', 'servicios', 'hogar'},
    },
    'inversion': {
        'label': 'Inversión',
        'group': GROUP_AHORRO,
        'inverted': True,
        # verde >=20%, amarillo >=10%, naranja >=5%, rojo <5%
        'thresholds': (Decimal('20.00'), Decimal('10.00'), Decimal('5.00'), Decimal('0.00')),
        'profiles': {'comercio', 'expansion', 'servicios', 'hogar'},
    },
}

# Valores recomendados "a ciencia casi cierta" según reglas de presupuesto
# ampliamente aceptadas (regla 50/30/20 de E. Warren; vivienda <=25-30%;
# fondo de emergencia 3-6 meses de gastos; inversión ~20%).
# thresholds (green, yellow, orange, red) en % del ingreso.
# Fuentes: Investopedia 50/30/20, Ramsey (vivienda <=25%), SoFi (alquiler+servicios <=30%),
# Vanguard (emergencia 3-6 meses). Contenido parafraseado para cumplir licencias.
RECOMMENDED_THRESHOLDS = {
    'alquiler': (Decimal('20.00'), Decimal('25.00'), Decimal('30.00'), Decimal('35.00')),
    'servicios': (Decimal('3.00'), Decimal('5.00'), Decimal('8.00'), Decimal('10.00')),
    'electricidad': (Decimal('2.00'), Decimal('3.00'), Decimal('5.00'), Decimal('7.00')),
    'agua': (Decimal('1.00'), Decimal('2.00'), Decimal('3.00'), Decimal('5.00')),
    'internet': (Decimal('1.00'), Decimal('2.00'), Decimal('3.00'), Decimal('5.00')),
    'mercaderia': (Decimal('35.00'), Decimal('45.00'), Decimal('50.00'), Decimal('60.00')),
    'salarios': (Decimal('18.00'), Decimal('22.00'), Decimal('28.00'), Decimal('35.00')),
    'seguros': (Decimal('3.00'), Decimal('5.00'), Decimal('7.00'), Decimal('10.00')),
    'impuestos_municipales': (Decimal('2.00'), Decimal('4.00'), Decimal('6.00'), Decimal('8.00')),
    'mantenimiento': (Decimal('3.00'), Decimal('5.00'), Decimal('8.00'), Decimal('10.00')),
    # Ahorros (invertidos)
    'emergencia': (Decimal('10.00'), Decimal('5.00'), Decimal('2.00'), Decimal('0.00')),
    'inversion': (Decimal('20.00'), Decimal('10.00'), Decimal('5.00'), Decimal('0.00')),
}


def is_inverted(key):
    """True si la categoría usa lógica invertida (ahorro: más es mejor)."""
    meta = CATEGORIES.get(key)
    return bool(meta and meta.get('inverted'))


def savings_categories():
    """Claves de categoría del grupo ahorro."""
    return categories_by_group(GROUP_AHORRO)


def recommended_thresholds(key):
    """Umbrales recomendados para una categoría, o None si no hay recomendación."""
    return RECOMMENDED_THRESHOLDS.get(key)

# Categoría especial para la ganancia neta (no es un gasto; umbrales invertidos)
NET_PROFIT_KEY = 'ganancia_neta'
NET_PROFIT_THRESHOLDS = (Decimal('20.00'), Decimal('10.00'), Decimal('5.00'), Decimal('0.00'))


def is_valid_profile(business_type):
    """True si el perfil existe en el catálogo."""
    return business_type in BUSINESS_PROFILES


def normalize_profile(business_type):
    """Devuelve un perfil válido; cae a DEFAULT_PROFILE si no lo es."""
    return business_type if is_valid_profile(business_type) else DEFAULT_PROFILE


def categories_for_profile(business_type):
    """Lista de claves de categoría que pertenecen por defecto a un perfil."""
    profile = normalize_profile(business_type)
    return [key for key, meta in CATEGORIES.items() if profile in meta['profiles']]


def default_thresholds_for_profile(business_type):
    """Dict {category: (green, yellow, orange, red)} para las categorías del perfil
    más la categoría especial ganancia_neta (siempre presente)."""
    result = {
        key: CATEGORIES[key]['thresholds']
        for key in categories_for_profile(business_type)
    }
    result[NET_PROFIT_KEY] = NET_PROFIT_THRESHOLDS
    return result


def all_categories():
    """Lista completa de claves de categoría de gasto (sin ganancia_neta)."""
    return list(CATEGORIES.keys())


def categories_by_group(group):
    """Claves de categoría de un grupo dado ('variable', 'operativo', ...)."""
    return [key for key, meta in CATEGORIES.items() if meta['group'] == group]


def variable_categories():
    return categories_by_group(GROUP_VARIABLE)


def operating_categories():
    return categories_by_group(GROUP_OPERATIVO)


def category_label(key):
    """Etiqueta en español de una categoría; title-case como fallback."""
    meta = CATEGORIES.get(key)
    if meta:
        return meta['label']
    return key.replace('_', ' ').title()


def category_group(key):
    meta = CATEGORIES.get(key)
    return meta['group'] if meta else GROUP_VARIABLE


def catalog_payload():
    """Representación serializable del catálogo completo para el frontend."""
    return {
        'profiles': {
            key: {'label': val['label'], 'description': val['description']}
            for key, val in BUSINESS_PROFILES.items()
        },
        'categories': {
            key: {
                'label': meta['label'],
                'group': meta['group'],
                'profiles': sorted(meta['profiles']),
            }
            for key, meta in CATEGORIES.items()
        },
    }
