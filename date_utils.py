"""
Shared date utility functions for the portfolio_manager package.

This module consolidates date handling logic that was previously duplicated
across multiple files (Property.py, Portfolio.py, Loan.py, PreferredEquity.py).
"""

import pandas as pd
from datetime import date, datetime
from calendar import monthrange
from typing import Optional


def ensure_end_of_month(input_date) -> Optional[date]:
    """
    Ensure the input is a datetime.date object and adjust to month-end.

    This is the unified version of ensure_date(), get_end_of_month(),
    and get_last_day_of_month() from various classes.

    Args:
        input_date: Date to convert (can be date, datetime, pd.Timestamp, or NaN/None)

    Returns:
        date object representing the last day of the month, or None if input is NaN/None

    Raises:
        ValueError: If input_date format is invalid

    Examples:
        >>> ensure_end_of_month(date(2023, 1, 15))
        date(2023, 1, 31)
        >>> ensure_end_of_month(pd.Timestamp('2023-02-10'))
        date(2023, 2, 28)
        >>> ensure_end_of_month(None)
        None
    """
    # Handle NaN, NaT, or None
    if input_date is None or pd.isna(input_date):
        return None

    # Convert to date object if needed
    if isinstance(input_date, pd.Timestamp):
        input_date = input_date.date()
    elif isinstance(input_date, datetime):
        input_date = input_date.date()
    elif not isinstance(input_date, date):
        raise ValueError(f"Invalid date format: {input_date}")

    # Ensure the date is the last day of the month
    last_day = monthrange(input_date.year, input_date.month)[1]
    return input_date.replace(day=last_day)


def validate_date(input_date) -> bool:
    """
    Check if the input is a valid date object.

    Args:
        input_date: Value to validate

    Returns:
        True if valid date, False otherwise
    """
    if input_date is None or pd.isna(input_date):
        return False

    return isinstance(input_date, (date, datetime, pd.Timestamp))


def convert_to_date(input_date) -> Optional[date]:
    """
    Convert various date formats to a standard date object without month-end adjustment.

    Args:
        input_date: Date to convert

    Returns:
        date object or None if input is NaN/None
    """
    if input_date is None or pd.isna(input_date):
        return None

    if isinstance(input_date, pd.Timestamp):
        return input_date.date()
    elif isinstance(input_date, datetime):
        return input_date.date()
    elif isinstance(input_date, date):
        return input_date
    else:
        raise ValueError(f"Invalid date format: {input_date}")
