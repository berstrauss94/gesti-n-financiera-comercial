"""Heatmap calculation service.

Traffic light colors:
  🟢 Green - Healthy
  🟡 Yellow - Caution
  🟠 Orange - Warning
  🔴 Red - Danger
  🚨 Critical - Emergency
  ⚪ Gray - Neutral (no data)
"""

HEATMAP_COLORS = {
    'green': '🟢',
    'yellow': '🟡',
    'orange': '🟠',
    'red': '🔴',
    'critical': '🚨',
    'neutral': '⚪',
}


def calculate_heatmap_color(percentage, thresholds):
    """Calculate heatmap color based on percentage and threshold config.

    Args:
        percentage: The percentage value to evaluate
        thresholds: Dict with keys 'green', 'yellow', 'orange', 'red'
                   containing upper bounds for each level

    Returns:
        Color key string
    """
    if percentage is None:
        return 'neutral'
    if percentage <= thresholds['green']:
        return 'green'
    elif percentage <= thresholds['yellow']:
        return 'yellow'
    elif percentage <= thresholds['orange']:
        return 'orange'
    elif percentage <= thresholds['red']:
        return 'red'
    else:
        return 'critical'
