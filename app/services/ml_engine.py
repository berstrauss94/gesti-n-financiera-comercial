"""ML Engine for financial predictions.

- Moving average: 90 days
- Recalibration trigger: variation > 10%
- Minimum records: 5
"""

import numpy as np
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app import db
from app.models.income import DailyIncome
from app.models.expense import VariableExpense, OperatingCost, Salary
from app.models.owner_withdrawal import OwnerWithdrawal
from app.models.ml_prediction import MLPrediction
from app.models.threshold_config import ThresholdConfig, DEFAULT_THRESHOLDS


ML_MOVING_AVERAGE_DAYS = 90
RECALIBRATION_THRESHOLD = 0.10
MIN_RECORDS = 5

# Valid categories for ML predictions
ML_CATEGORIES = [
    'ingresos',
    'salarios',
    'retiros_dueno',
    'comisiones',
    'mermas',
    'servicios',
    'insumos',
    'mantenimiento',
    'impuestos_municipales',
    'seguros',
    'logistica',
    'electricidad',
    'monotributo',
    'mercaderia',
    'alquiler',
    'contable',
]


def calculate_moving_average(values, window=ML_MOVING_AVERAGE_DAYS):
    """Calculate moving average for a series of values.

    Args:
        values: List of numeric values (chronologically ordered)
        window: Number of days for the moving average

    Returns:
        List of moving average values, or None if insufficient data
    """
    if len(values) < MIN_RECORDS:
        return None

    arr = np.array(values, dtype=float)
    window = min(window, len(arr))

    weights = np.ones(window) / window
    return np.convolve(arr, weights, mode='valid').tolist()


def needs_recalibration(current_value, predicted_value):
    """Determine if model needs recalibration.

    Args:
        current_value: Actual observed value
        predicted_value: Model's predicted value

    Returns:
        True if variation exceeds threshold (10%)
    """
    if predicted_value == 0:
        return current_value != 0

    variation = abs(current_value - predicted_value) / abs(predicted_value)
    return variation > RECALIBRATION_THRESHOLD


def _fetch_category_values(business_id, category, days=ML_MOVING_AVERAGE_DAYS):
    """Fetch the last N days of data for a given category.

    Returns a list of (date, float_amount) tuples ordered chronologically.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    if category == 'ingresos':
        records = DailyIncome.query.filter(
            DailyIncome.business_id == business_id,
            DailyIncome.date >= start_date,
            DailyIncome.date <= end_date,
        ).order_by(DailyIncome.date.asc()).all()
        return [(r.date, float(r.amount)) for r in records]

    elif category == 'salarios':
        records = Salary.query.filter(
            Salary.business_id == business_id,
            Salary.period_start >= start_date,
            Salary.period_start <= end_date,
        ).order_by(Salary.period_start.asc()).all()
        return [(r.period_start, float(r.amount)) for r in records]

    elif category == 'retiros_dueno':
        records = OwnerWithdrawal.query.filter(
            OwnerWithdrawal.business_id == business_id,
            OwnerWithdrawal.date >= start_date,
            OwnerWithdrawal.date <= end_date,
        ).order_by(OwnerWithdrawal.date.asc()).all()
        return [(r.date, float(r.amount)) for r in records]

    elif category in ('electricidad', 'monotributo', 'mercaderia', 'alquiler', 'contable'):
        # Operating costs
        records = OperatingCost.query.filter(
            OperatingCost.business_id == business_id,
            OperatingCost.category == category,
            OperatingCost.month >= start_date,
            OperatingCost.month <= end_date,
        ).order_by(OperatingCost.month.asc()).all()
        return [(r.month, float(r.amount)) for r in records]

    else:
        # Variable expenses (comisiones, mermas, servicios, insumos, etc.)
        records = VariableExpense.query.filter(
            VariableExpense.business_id == business_id,
            VariableExpense.category == category,
            VariableExpense.date >= start_date,
            VariableExpense.date <= end_date,
        ).order_by(VariableExpense.date.asc()).all()
        return [(r.date, float(r.amount)) for r in records]


def predict_next_period(business_id, category):
    """Generate prediction using moving average with confidence interval.

    Args:
        business_id: The business ID to predict for
        category: The financial category to predict

    Returns:
        dict with prediction results or insufficient data indicator
    """
    # Fetch last 90 days of data
    data_points = _fetch_category_values(business_id, category)

    if len(data_points) < MIN_RECORDS:
        return {
            'status': 'insufficient_data',
            'error_code': 'ML_INSUFFICIENT_DATA',
            'message': 'Datos insuficientes, se requieren mínimo 5 registros',
            'records_found': len(data_points),
            'records_required': MIN_RECORDS,
        }

    values = [v for _, v in data_points]

    # Calculate moving average
    ma = calculate_moving_average(values)

    if ma is None or len(ma) == 0:
        return {
            'status': 'insufficient_data',
            'error_code': 'ML_INSUFFICIENT_DATA',
            'message': 'Datos insuficientes, se requieren mínimo 5 registros',
            'records_found': len(data_points),
            'records_required': MIN_RECORDS,
        }

    # Predicted value is the last moving average value
    predicted = ma[-1]

    # Calculate residuals (difference between actual and MA values)
    # Residuals are calculated over the portion where MA is defined
    ma_start_idx = len(values) - len(ma)
    actual_aligned = values[ma_start_idx:]
    residuals = [actual - avg for actual, avg in zip(actual_aligned, ma)]

    # Standard deviation of residuals
    std_residuals = float(np.std(residuals)) if len(residuals) > 1 else 0.0

    # 95% confidence interval: predicted ± 1.96 * std
    confidence_lower = predicted - 1.96 * std_residuals
    confidence_upper = predicted + 1.96 * std_residuals

    # Ensure lower bound is not negative for financial amounts
    confidence_lower = max(0.0, confidence_lower)

    # Determine trend based on MA slope
    trend = _determine_trend(ma)

    # Check recalibration need (compare last actual value vs predicted)
    last_actual = values[-1]
    should_recalibrate = needs_recalibration(last_actual, predicted)

    # Store prediction in database
    today = date.today()
    target = today + timedelta(days=30)  # Predict next month

    prediction_record = MLPrediction(
        business_id=business_id,
        category=category,
        predicted_value=Decimal(str(round(predicted, 2))),
        confidence_lower=Decimal(str(round(confidence_lower, 2))),
        confidence_upper=Decimal(str(round(confidence_upper, 2))),
        prediction_date=today,
        target_date=target,
        recalibrated=False,
    )
    db.session.add(prediction_record)
    db.session.commit()

    return {
        'status': 'success',
        'category': category,
        'predicted_value': round(predicted, 2),
        'confidence_lower': round(confidence_lower, 2),
        'confidence_upper': round(confidence_upper, 2),
        'trend': trend,
        'needs_recalibration': should_recalibrate,
        'data_points_used': len(values),
        'prediction_date': today.isoformat(),
        'target_date': target.isoformat(),
    }


def _determine_trend(ma_values):
    """Determine trend direction from moving average values.

    Uses the slope of the last few MA values to determine direction.

    Returns:
        'up', 'down', or 'stable'
    """
    if len(ma_values) < 2:
        return 'stable'

    # Use last 5 values (or all if fewer) to determine trend
    recent = ma_values[-min(5, len(ma_values)):]

    # Calculate simple slope using first and last of recent values
    slope = (recent[-1] - recent[0]) / len(recent)

    # Normalize slope relative to the average value to get percentage change
    avg_value = np.mean(recent)
    if avg_value == 0:
        return 'stable'

    relative_slope = slope / avg_value

    # Threshold: ±2% change is considered significant
    if relative_slope > 0.02:
        return 'up'
    elif relative_slope < -0.02:
        return 'down'
    else:
        return 'stable'


def recalibrate(business_id, category):
    """Recalibrate thresholds for a category based on actual data patterns.

    Only updates non-custom thresholds (is_custom=False).
    Adjusts thresholds based on the statistical distribution of actual data.

    Args:
        business_id: The business ID
        category: The category to recalibrate

    Returns:
        dict with recalibration results
    """
    # Fetch threshold config
    config = ThresholdConfig.query.filter_by(
        business_id=business_id,
        category=category,
    ).first()

    if config is None:
        return {
            'status': 'error',
            'message': f'No threshold configuration found for category: {category}',
        }

    if config.is_custom:
        return {
            'status': 'skipped',
            'message': 'Custom thresholds are not auto-recalibrated',
            'category': category,
        }

    # Fetch historical data for the category
    data_points = _fetch_category_values(business_id, category, days=180)

    if len(data_points) < MIN_RECORDS:
        return {
            'status': 'insufficient_data',
            'message': 'Datos insuficientes para recalibrar',
            'records_found': len(data_points),
        }

    values = [v for _, v in data_points]
    mean_val = float(np.mean(values))
    std_val = float(np.std(values))

    # Recalibrate thresholds based on statistical distribution
    # green_max: mean + 0.5 * std (normal range)
    # yellow_max: mean + 1.0 * std (slightly above normal)
    # orange_max: mean + 1.5 * std (concerning)
    # red_max: mean + 2.0 * std (critical threshold)
    # Note: These are percentages, but we adjust based on actual patterns
    if mean_val > 0:
        # Get income data to calculate percentage-based thresholds
        income_data = _fetch_category_values(business_id, 'ingresos', days=180)
        if len(income_data) >= MIN_RECORDS:
            avg_income = float(np.mean([v for _, v in income_data]))
            if avg_income > 0:
                # Calculate actual percentage this category represents
                actual_pct = (mean_val / avg_income) * 100
                pct_std = (std_val / avg_income) * 100

                new_green = round(actual_pct + 0.5 * pct_std, 2)
                new_yellow = round(actual_pct + 1.0 * pct_std, 2)
                new_orange = round(actual_pct + 1.5 * pct_std, 2)
                new_red = round(actual_pct + 2.0 * pct_std, 2)

                config.green_max = Decimal(str(new_green))
                config.yellow_max = Decimal(str(new_yellow))
                config.orange_max = Decimal(str(new_orange))
                config.red_max = Decimal(str(new_red))
                config.updated_at = datetime.now(timezone.utc)

                db.session.commit()

                # Mark the latest prediction as recalibrated
                latest_prediction = MLPrediction.query.filter_by(
                    business_id=business_id,
                    category=category,
                ).order_by(MLPrediction.created_at.desc()).first()

                if latest_prediction:
                    latest_prediction.recalibrated = True
                    db.session.commit()

                return {
                    'status': 'success',
                    'category': category,
                    'new_thresholds': {
                        'green_max': new_green,
                        'yellow_max': new_yellow,
                        'orange_max': new_orange,
                        'red_max': new_red,
                    },
                    'based_on_records': len(values),
                }

    return {
        'status': 'skipped',
        'message': 'Insufficient income data for percentage-based recalibration',
        'category': category,
    }


def get_all_trends(business_id):
    """Get trend predictions for all categories.

    Returns a summary of predictions for each category with sufficient data.
    """
    results = {}

    for category in ML_CATEGORIES:
        data_points = _fetch_category_values(business_id, category)

        if len(data_points) < MIN_RECORDS:
            results[category] = {
                'status': 'insufficient_data',
                'records_found': len(data_points),
            }
            continue

        values = [v for _, v in data_points]
        ma = calculate_moving_average(values)

        if ma is None or len(ma) == 0:
            results[category] = {
                'status': 'insufficient_data',
                'records_found': len(data_points),
            }
            continue

        trend = _determine_trend(ma)
        current_avg = round(ma[-1], 2)

        results[category] = {
            'status': 'success',
            'trend': trend,
            'current_average': current_avg,
            'data_points': len(values),
        }

    return results
