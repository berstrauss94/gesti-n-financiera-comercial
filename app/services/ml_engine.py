"""ML Engine for financial predictions.

- Moving average: 90 days
- Recalibration trigger: variation > 10%
- Minimum records: 5
"""

import numpy as np
from datetime import date, timedelta


ML_MOVING_AVERAGE_DAYS = 90
RECALIBRATION_THRESHOLD = 0.10
MIN_RECORDS = 5


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
    if len(arr) < window:
        window = len(arr)

    weights = np.ones(window) / window
    return np.convolve(arr, weights, mode='valid').tolist()


def needs_recalibration(current_value, predicted_value):
    """Determine if model needs recalibration.

    Args:
        current_value: Actual observed value
        predicted_value: Model's predicted value

    Returns:
        True if variation exceeds threshold
    """
    if predicted_value == 0:
        return current_value != 0

    variation = abs(current_value - predicted_value) / abs(predicted_value)
    return variation > RECALIBRATION_THRESHOLD
