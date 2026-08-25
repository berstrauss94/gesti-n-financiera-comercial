"""Unit tests for Marshmallow validation schemas."""
import pytest
from decimal import Decimal
from app.schemas import (
    UserRegistrationSchema,
    LoginSchema,
    IncomeSchema,
    SalarySchema,
    OwnerWithdrawalSchema,
    VariableExpenseSchema,
    OperatingCostSchema,
    ThresholdConfigSchema,
    ReportQuerySchema,
    VALIDATION_USERNAME_LENGTH,
    VALIDATION_USERNAME_UPPERCASE,
    VALIDATION_EMAIL_FORMAT,
    VALIDATION_PHONE_FORMAT,
    VALIDATION_AMOUNT_RANGE,
    VALIDATION_INVALID_CATEGORY,
)


class TestUserRegistrationSchema:
    """Tests for user registration validation."""

    def setup_method(self):
        self.schema = UserRegistrationSchema()

    def test_valid_registration(self):
        data = {
            'username': 'TestUser1',
            'email': 'test@example.com',
            'password': 'securepass123',
            'phone': '+591 70012345',
        }
        result = self.schema.load(data)
        assert result['username'] == 'TestUser1'
        assert result['email'] == 'test@example.com'

    def test_username_too_short(self):
        data = {'username': 'Short1', 'email': 'test@example.com', 'password': 'pass123'}
        errors = self.schema.validate(data)
        assert 'username' in errors
        assert VALIDATION_USERNAME_LENGTH in errors['username']

    def test_username_exactly_8_chars_valid(self):
        data = {'username': 'Abcdefgh', 'email': 'test@example.com', 'password': 'pass123'}
        errors = self.schema.validate(data)
        assert 'username' not in errors

    def test_username_7_chars_invalid(self):
        data = {'username': 'Abcdefg', 'email': 'test@example.com', 'password': 'pass123'}
        errors = self.schema.validate(data)
        assert 'username' in errors
        assert VALIDATION_USERNAME_LENGTH in errors['username']

    def test_username_no_uppercase(self):
        data = {'username': 'alllower', 'email': 'test@example.com', 'password': 'pass123'}
        errors = self.schema.validate(data)
        assert 'username' in errors
        assert VALIDATION_USERNAME_UPPERCASE in errors['username']

    def test_username_with_uppercase_valid(self):
        data = {'username': 'hasUppercase', 'email': 'test@example.com', 'password': 'pass123'}
        errors = self.schema.validate(data)
        assert 'username' not in errors

    def test_email_invalid_format(self):
        data = {'username': 'ValidUser', 'email': 'not-an-email', 'password': 'pass123'}
        errors = self.schema.validate(data)
        assert 'email' in errors
        assert VALIDATION_EMAIL_FORMAT in errors['email']

    def test_email_missing_at(self):
        data = {'username': 'ValidUser', 'email': 'testexample.com', 'password': 'pass123'}
        errors = self.schema.validate(data)
        assert 'email' in errors

    def test_email_valid(self):
        data = {'username': 'ValidUser', 'email': 'user@domain.co', 'password': 'pass123'}
        errors = self.schema.validate(data)
        assert 'email' not in errors

    def test_phone_too_few_digits(self):
        data = {
            'username': 'ValidUser',
            'email': 'test@example.com',
            'password': 'pass123',
            'phone': '123456',  # only 6 digits
        }
        errors = self.schema.validate(data)
        assert 'phone' in errors
        assert VALIDATION_PHONE_FORMAT in errors['phone']

    def test_phone_too_many_digits(self):
        data = {
            'username': 'ValidUser',
            'email': 'test@example.com',
            'password': 'pass123',
            'phone': '1234567890123456',  # 16 digits
        }
        errors = self.schema.validate(data)
        assert 'phone' in errors
        assert VALIDATION_PHONE_FORMAT in errors['phone']

    def test_phone_valid_with_formatting(self):
        data = {
            'username': 'ValidUser',
            'email': 'test@example.com',
            'password': 'pass123',
            'phone': '+591 700-12345',  # 10 digits after stripping
        }
        errors = self.schema.validate(data)
        assert 'phone' not in errors

    def test_phone_exactly_7_digits_valid(self):
        data = {
            'username': 'ValidUser',
            'email': 'test@example.com',
            'password': 'pass123',
            'phone': '1234567',
        }
        errors = self.schema.validate(data)
        assert 'phone' not in errors

    def test_phone_exactly_15_digits_valid(self):
        data = {
            'username': 'ValidUser',
            'email': 'test@example.com',
            'password': 'pass123',
            'phone': '123456789012345',
        }
        errors = self.schema.validate(data)
        assert 'phone' not in errors


class TestIncomeSchema:
    """Tests for income validation."""

    def setup_method(self):
        self.schema = IncomeSchema()

    def test_valid_income(self):
        data = {'amount': '1500.50', 'date': '2024-01-15'}
        result = self.schema.load(data)
        assert result['amount'] == Decimal('1500.50')

    def test_amount_too_low(self):
        data = {'amount': '0.00', 'date': '2024-01-15'}
        errors = self.schema.validate(data)
        assert 'amount' in errors
        assert VALIDATION_AMOUNT_RANGE in errors['amount']

    def test_amount_too_high(self):
        data = {'amount': '1000000000.00', 'date': '2024-01-15'}
        errors = self.schema.validate(data)
        assert 'amount' in errors
        assert VALIDATION_AMOUNT_RANGE in errors['amount']

    def test_amount_min_boundary(self):
        data = {'amount': '0.01', 'date': '2024-01-15'}
        errors = self.schema.validate(data)
        assert 'amount' not in errors

    def test_amount_max_boundary(self):
        data = {'amount': '999999999.99', 'date': '2024-01-15'}
        errors = self.schema.validate(data)
        assert 'amount' not in errors


class TestVariableExpenseSchema:
    """Tests for variable expense validation."""

    def setup_method(self):
        self.schema = VariableExpenseSchema()

    def test_valid_expense(self):
        data = {
            'category': 'comisiones',
            'amount': '250.00',
            'date': '2024-01-15',
        }
        result = self.schema.load(data)
        assert result['category'] == 'comisiones'

    def test_invalid_category(self):
        data = {
            'category': 'invalida',
            'amount': '250.00',
            'date': '2024-01-15',
        }
        errors = self.schema.validate(data)
        assert 'category' in errors
        assert VALIDATION_INVALID_CATEGORY in errors['category']

    def test_all_valid_categories(self):
        valid_categories = [
            'comisiones', 'mermas', 'servicios', 'insumos',
            'mantenimiento', 'impuestos_municipales', 'seguros', 'logistica',
        ]
        for cat in valid_categories:
            data = {'category': cat, 'amount': '100.00', 'date': '2024-01-15'}
            errors = self.schema.validate(data)
            assert 'category' not in errors, f"Category '{cat}' should be valid"


class TestOperatingCostSchema:
    """Tests for operating cost validation."""

    def setup_method(self):
        self.schema = OperatingCostSchema()

    def test_valid_operating_cost(self):
        data = {
            'category': 'electricidad',
            'amount': '500.00',
            'month': '2024-01-01',
        }
        result = self.schema.load(data)
        assert result['category'] == 'electricidad'

    def test_invalid_category(self):
        data = {
            'category': 'internet',
            'amount': '100.00',
            'month': '2024-01-01',
        }
        errors = self.schema.validate(data)
        assert 'category' in errors
        assert VALIDATION_INVALID_CATEGORY in errors['category']


class TestLoginSchema:
    """Tests for login validation."""

    def setup_method(self):
        self.schema = LoginSchema()

    def test_valid_login(self):
        data = {'username': 'testuser', 'password': 'pass123'}
        result = self.schema.load(data)
        assert result['username'] == 'testuser'

    def test_missing_username(self):
        data = {'password': 'pass123'}
        errors = self.schema.validate(data)
        assert 'username' in errors

    def test_missing_password(self):
        data = {'username': 'testuser'}
        errors = self.schema.validate(data)
        assert 'password' in errors
