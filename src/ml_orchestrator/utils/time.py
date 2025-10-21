from typing import Optional

def build_cron_expression(
    minute: str = "*",
    hour: str = "*",
    day_of_month: str = "*",
    month: str = "*",
    day_of_week: str = "*",
) -> str:
    """Builds a cron expression string from individual time components.

    Each component can be a specific value (e.g., '0', '15'), a list of values
    (e.g., '0,30'), a range (e.g., '9-17'), a step (e.g., '*/5'), or '*' for all.
    All values are interpreted in UTC.

    Args:
        minute: Minute (0-59 or '*').
        hour: Hour (0-23 or '*').
        day_of_month: Day of month (1-31 or '*').
        month: Month (1-12 or '*' or JAN-DEC).
        day_of_week: Day of week (0-6 or '*' or SUN-SAT, 0 and 7 are Sunday).

    Returns:
        A cron expression string.

    Examples:
        >>> build_cron_expression(minute="30", hour="3")
        '30 3 * * *'  # Daily at 3:30 AM UTC
        >>> build_cron_expression(minute="0", hour="9", day_of_week="1")
        '0 9 * * 1'   # Every Monday at 9:00 AM UTC
        >>> build_cron_expression(minute="*/15")
        '*/15 * * * *' # Every 15 minutes
    """
    return f"{minute} {hour} {day_of_month} {month} {day_of_week}"