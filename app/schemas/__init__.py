"""Marshmallow schemas for input validation."""
import re
from marshmallow import Schema, fields, validate, validates, ValidationError


# Valid categories for variable expenses
VALID_VARIABLE_EXPENSE_CATEGORIES = [
    'comisiones', 'mermas', 'servicios', 'insumos',
    'mantenimiento', 'impuestos_municipales', 'seguros', 'logistica',
]

# Valid categories for operating costs
VALID_OPERATING_COST_CATEGORIES = [
    'electricidad', 'monotributo', 'mercaderia', 'alquiler', 'contable',
]

# Validation error messages in Spanish
VALIDATION_USERNAME_LENGTH = "Username debe tener mínimo 8 caracteres"
VALIDATION_USERNAME_UPPERCASE = "Username debe contener al menos una mayúscula"
VALIDATION_EMAIL_FORMAT = "Email inválido"
VALIDATION_PHONE_FORMAT = "Número de celular debe tener entre 7 y 15 dígitos"
VALIDATION_AMOUNT_RANGE = "Monto debe estar entre 0.01 y 999,999,999.99"
VALIDATION_INVALID_CATEGORY = "Categoría no válida"

# RFC 5322 email regex pattern
EMAIL_RFC5322_PATTERN = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)


class UserRegistrationSchema(Schema):
    """Schema for user registration validation."""

    username = fields.String(required=True)
    email = fields.String(required=True)
    password = fields.String(required=True, validate=validate.Length(min=1))
    phone = fields.String(required=False, allow_none=True)

    @validates('username')
    def validate_username(self, value, **kwargs):
        """Validate username: min 8 chars, at least one uppercase letter."""
        if len(value) < 8:
            raise ValidationError(VALIDATION_USERNAME_LENGTH)
        if not any(c.isupper() for c in value):
            raise ValidationError(VALIDATION_USERNAME_UPPERCASE)

    @validates('email')
    def validate_email(self, value, **kwargs):
        """Validate email against RFC 5322 pattern."""
        if not EMAIL_RFC5322_PATTERN.match(value):
            raise ValidationError(VALIDATION_EMAIL_FORMAT)

    @validates('phone')
    def validate_phone(self, value, **kwargs):
        """Validate phone: 7-15 digits after stripping non-digit chars."""
        if value is None:
            return
        digits = re.sub(r'\D', '', value)
        if len(digits) < 7 or len(digits) > 15:
            raise ValidationError(VALIDATION_PHONE_FORMAT)


class LoginSchema(Schema):
    """Schema for login validation."""

    username = fields.String(required=True, validate=validate.Length(min=1))
    password = fields.String(required=True, validate=validate.Length(min=1))


class IncomeSchema(Schema):
    """Schema for daily income validation."""

    amount = fields.Decimal(required=True, as_string=False)
    date = fields.Date(required=True)
    notes = fields.String(required=False, allow_none=True)

    @validates('amount')
    def validate_amount(self, value, **kwargs):
        """Validate amount is between 0.01 and 999,999,999.99."""
        from decimal import Decimal
        min_val = Decimal('0.01')
        max_val = Decimal('999999999.99')
        if value < min_val or value > max_val:
            raise ValidationError(VALIDATION_AMOUNT_RANGE)


class SalarySchema(Schema):
    """Schema for employee salary validation."""

    employee_name = fields.String(required=True, validate=validate.Length(min=1))
    amount = fields.Decimal(required=True, as_string=False)
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)

    @validates('amount')
    def validate_amount(self, value, **kwargs):
        """Validate amount is between 0.01 and 999,999,999.99."""
        from decimal import Decimal
        min_val = Decimal('0.01')
        max_val = Decimal('999999999.99')
        if value < min_val or value > max_val:
            raise ValidationError(VALIDATION_AMOUNT_RANGE)


class OwnerWithdrawalSchema(Schema):
    """Schema for owner withdrawal validation."""

    amount = fields.Decimal(required=True, as_string=False)
    date = fields.Date(required=True)
    description = fields.String(required=False, allow_none=True)

    @validates('amount')
    def validate_amount(self, value, **kwargs):
        """Validate amount is between 0.01 and 999,999,999.99."""
        from decimal import Decimal
        min_val = Decimal('0.01')
        max_val = Decimal('999999999.99')
        if value < min_val or value > max_val:
            raise ValidationError(VALIDATION_AMOUNT_RANGE)


class VariableExpenseSchema(Schema):
    """Schema for variable expense validation (8 categories)."""

    category = fields.String(required=True)
    amount = fields.Decimal(required=True, as_string=False)
    date = fields.Date(required=True)
    description = fields.String(required=False, allow_none=True)

    @validates('category')
    def validate_category(self, value, **kwargs):
        """Validate category is one of 8 valid values."""
        if value not in VALID_VARIABLE_EXPENSE_CATEGORIES:
            raise ValidationError(VALIDATION_INVALID_CATEGORY)

    @validates('amount')
    def validate_amount(self, value, **kwargs):
        """Validate amount is between 0.01 and 999,999,999.99."""
        from decimal import Decimal
        min_val = Decimal('0.01')
        max_val = Decimal('999999999.99')
        if value < min_val or value > max_val:
            raise ValidationError(VALIDATION_AMOUNT_RANGE)


class OperatingCostSchema(Schema):
    """Schema for operating cost validation."""

    category = fields.String(required=True)
    amount = fields.Decimal(required=True, as_string=False)
    month = fields.Date(required=True)
    description = fields.String(required=False, allow_none=True)

    @validates('category')
    def validate_category(self, value, **kwargs):
        """Validate category is one of the valid operating cost categories."""
        if value not in VALID_OPERATING_COST_CATEGORIES:
            raise ValidationError(VALIDATION_INVALID_CATEGORY)

    @validates('amount')
    def validate_amount(self, value, **kwargs):
        """Validate amount is between 0.01 and 999,999,999.99."""
        from decimal import Decimal
        min_val = Decimal('0.01')
        max_val = Decimal('999999999.99')
        if value < min_val or value > max_val:
            raise ValidationError(VALIDATION_AMOUNT_RANGE)


class ThresholdConfigSchema(Schema):
    """Schema for threshold configuration validation."""

    category = fields.String(required=True, validate=validate.Length(min=1))
    green_max = fields.Decimal(required=True, as_string=False)
    yellow_max = fields.Decimal(required=True, as_string=False)
    orange_max = fields.Decimal(required=True, as_string=False)
    red_max = fields.Decimal(required=True, as_string=False)


class ReportQuerySchema(Schema):
    """Schema for report query parameters validation."""

    granularity = fields.String(
        required=False,
        validate=validate.OneOf(
            ['daily', 'weekly', 'monthly', 'quarterly', 'semiannual', 'annual']
        ),
    )
    from_date = fields.Date(required=False, data_key='from')
    to_date = fields.Date(required=False, data_key='to')
    filter = fields.String(required=False, allow_none=True)


__all__ = [
    'UserRegistrationSchema',
    'LoginSchema',
    'IncomeSchema',
    'SalarySchema',
    'OwnerWithdrawalSchema',
    'VariableExpenseSchema',
    'OperatingCostSchema',
    'ThresholdConfigSchema',
    'ReportQuerySchema',
    'VALID_VARIABLE_EXPENSE_CATEGORIES',
    'VALID_OPERATING_COST_CATEGORIES',
    'VALIDATION_USERNAME_LENGTH',
    'VALIDATION_USERNAME_UPPERCASE',
    'VALIDATION_EMAIL_FORMAT',
    'VALIDATION_PHONE_FORMAT',
    'VALIDATION_AMOUNT_RANGE',
    'VALIDATION_INVALID_CATEGORY',
]
