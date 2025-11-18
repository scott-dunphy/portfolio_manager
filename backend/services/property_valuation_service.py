from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime
from calendar import monthrange
from typing import Dict, List, Optional

from dateutil.relativedelta import relativedelta

from models import Portfolio, Property


def calculate_property_valuation(property_obj: Property) -> Dict[str, object]:
    portfolio: Optional[Portfolio] = property_obj.portfolio or Portfolio.query.get(
        property_obj.portfolio_id
    )
    if not portfolio or not portfolio.analysis_start_date or not portfolio.analysis_end_date:
        return {"year1_cap_rate": None, "monthly_market_values": []}

    start_month = _month_end(portfolio.analysis_start_date)
    end_month = _month_end(portfolio.analysis_end_date)
    extended_end = _month_end(end_month + relativedelta(years=11))

    monthly_noi = _project_monthly_noi(property_obj, start_month, extended_end)
    if not monthly_noi:
        return {"year1_cap_rate": None, "monthly_market_values": []}

    months = list(monthly_noi.keys())
    purchase_month = _month_end(property_obj.purchase_date) if property_obj.purchase_date else None
    forward_noi = _calculate_forward_noi(months, monthly_noi, purchase_month)

    market_value_start = property_obj.market_value_start or 0.0
    first_month = months[0]
    forward_first_year = forward_noi.get(first_month)
    year1_cap = None
    if market_value_start and forward_first_year:
        year1_cap = forward_first_year / market_value_start if market_value_start else None

    exit_cap = property_obj.exit_cap_rate
    exit_month = _month_end(property_obj.exit_date) if property_obj.exit_date else end_month

    monthly_values: List[dict] = []
    override_price = property_obj.disposition_price_override
    for month in months:
        if month > end_month:
            break
        cap_rate = _interpolated_cap_rate(year1_cap, exit_cap, start_month, month, exit_month)
        market_value = (forward_noi[month] / cap_rate) if cap_rate else None
        if (
            override_price is not None
            and exit_month is not None
            and month == exit_month
        ):
            market_value = override_price
        monthly_values.append(
            {
                "date": month.isoformat(),
                "forward_noi_12m": round(forward_noi[month], 2),
                "cap_rate": cap_rate,
                "market_value": round(market_value, 2) if market_value is not None else None,
            }
        )

    return {
        "year1_cap_rate": year1_cap,
        "monthly_market_values": monthly_values,
    }


def _project_monthly_noi(
    property_obj: Property,
    start_month: date,
    end_month: date,
) -> "OrderedDict[date, float]":
    manual_entries = list(property_obj.manual_cash_flows or [])
    use_manual = bool(property_obj.use_manual_noi_capex and manual_entries)
    manual_by_month = {
        (entry.year, entry.month): entry for entry in manual_entries if entry.month
    }
    manual_by_year = {
        entry.year: entry for entry in manual_entries if not entry.month
    }

    result: "OrderedDict[date, float]" = OrderedDict()

    purchase_month = _month_end(property_obj.purchase_date) if property_obj.purchase_date else None
    exit_month = _month_end(property_obj.exit_date) if property_obj.exit_date else None
    growth_base = _month_end(_resolve_property_start_date(property_obj)) or start_month

    current = start_month
    while current <= end_month:
        manual_value = None
        if use_manual:
            entry = manual_by_month.get((current.year, current.month))
            if entry:
                manual_value = entry.annual_noi or 0.0
            else:
                annual_entry = manual_by_year.get(current.year)
                if annual_entry and annual_entry.annual_noi is not None:
                    manual_value = (annual_entry.annual_noi or 0.0) / 12.0

        if manual_value is not None:
            monthly_noi = manual_value
        elif purchase_month and current < purchase_month:
            # Before purchase, NOI is zero
            monthly_noi = 0.0
        else:
            # Project NOI for owned periods and beyond exit for valuation purposes
            # The exit_date will be used for cap rate interpolation and output filtering,
            # but NOI should continue growing for forward 12-month NOI calculation at exit
            initial_noi = property_obj.initial_noi
            growth = property_obj.noi_growth_rate or 0.0
            if initial_noi is None:
                monthly_noi = 0.0
            else:
                months_since_start = max(
                    0, (current.year - growth_base.year) * 12 + (current.month - growth_base.month)
                )
                # Apply growth only after each full year has passed so the first
                # 12 months remain flat at the initial NOI value.
                full_years_elapsed = (months_since_start - 1) // 12 if months_since_start > 0 else 0
                annual_noi = initial_noi * ((1 + growth) ** full_years_elapsed)
                monthly_noi = annual_noi / 12.0

        result[current] = monthly_noi or 0.0
        current = _month_end(current + relativedelta(months=1))

    return result


def _calculate_forward_noi(
    months: List[date],
    monthly_noi: Dict[date, float],
    purchase_month: Optional[date] = None
) -> Dict[date, float]:
    """
    Calculate forward 12-month NOI for each month.

    The forward 12-month window starts from the month immediately AFTER the
    current month because we want true "forward-looking" NOI. Months prior
    to an acquisition date should not carry any forward NOI.
    """
    totals: Dict[date, float] = {}
    for idx, month in enumerate(months):
        # Do not project NOI before the property is acquired
        if purchase_month and month < purchase_month:
            totals[month] = 0.0
            continue

        total = 0.0
        start_offset = 1  # Always look strictly forward

        # Sum the 12 months starting right after the current month
        for offset in range(start_offset, start_offset + 12):
            target_index = idx + offset
            if target_index >= len(months):
                break
            total += monthly_noi[months[target_index]]

        totals[month] = total
    return totals


def _interpolated_cap_rate(
    year1_cap: Optional[float],
    exit_cap: Optional[float],
    start_month: date,
    target_month: date,
    exit_month: Optional[date],
) -> Optional[float]:
    if exit_cap is None or exit_cap <= 0:
        return year1_cap

    if year1_cap is None:
        return exit_cap

    if not exit_month or exit_month <= start_month:
        return exit_cap

    total_months = max(1, _months_between(start_month, exit_month))
    elapsed = max(0, min(total_months, _months_between(start_month, target_month)))
    t = min(1.0, elapsed / total_months)
    return year1_cap + (exit_cap - year1_cap) * t


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def _resolve_property_start_date(property_obj: Property) -> Optional[date]:
    if property_obj.purchase_date:
        return property_obj.purchase_date
    portfolio = property_obj.portfolio or Portfolio.query.get(property_obj.portfolio_id)
    if portfolio and portfolio.analysis_start_date:
        return portfolio.analysis_start_date
    return None


def _month_end(value: Optional[date]) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.date()
    last_day = monthrange(value.year, value.month)[1]
    return value.replace(day=last_day)
