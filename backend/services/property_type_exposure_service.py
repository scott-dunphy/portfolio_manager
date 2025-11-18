from __future__ import annotations
from collections import defaultdict, OrderedDict
from datetime import date
from typing import Dict, List, Optional
from dateutil.relativedelta import relativedelta

from models import Portfolio, Property
from services.property_valuation_service import calculate_property_valuation, _month_end


def calculate_property_type_exposure(portfolio_id: int) -> Dict[str, object]:
    """
    Calculate property type exposure over time using market value at share,
    showing only quarter-end months as percentages summing to 100%.

    Returns a dictionary with:
    - dates: List of quarter-end dates in the analysis period
    - property_types: List of unique property types
    - data: List of dicts with date and percentage exposure for each property type
    """
    portfolio = Portfolio.query.get(portfolio_id)
    if not portfolio or not portfolio.analysis_start_date or not portfolio.analysis_end_date:
        return {
            "dates": [],
            "property_types": [],
            "data": []
        }

    properties = Property.query.filter_by(portfolio_id=portfolio_id).all()
    if not properties:
        return {
            "dates": [],
            "property_types": [],
            "data": []
        }

    # Generate monthly dates from analysis start to end
    start_month = _month_end(portfolio.analysis_start_date)
    end_month = _month_end(portfolio.analysis_end_date)

    # Filter to only quarter-end months (March, June, September, December)
    quarter_end_dates = []
    current = start_month
    while current <= end_month:
        if current.month in [3, 6, 9, 12]:
            quarter_end_dates.append(current)
        current = _month_end(current + relativedelta(months=1))

    if not quarter_end_dates:
        return {
            "dates": [],
            "property_types": [],
            "data": []
        }

    # Get all property types
    property_types = list(set(p.property_type for p in properties if p.property_type))
    property_types.sort()

    # Calculate market values for each property at each quarter-end date
    exposure_by_type = {ptype: {} for ptype in property_types}

    for date_point in quarter_end_dates:
        total_value = 0.0
        type_values = {ptype: 0.0 for ptype in property_types}

        for prop in properties:
            if not prop.property_type:
                continue

            purchase_month = _month_end(prop.purchase_date) if prop.purchase_date else None
            exit_month = _month_end(prop.exit_date) if prop.exit_date else None
            if purchase_month and date_point < purchase_month:
                continue
            if exit_month and date_point > exit_month:
                continue

            # Get valuation data for this property
            valuation = calculate_property_valuation(prop)
            monthly_values = valuation.get("monthly_market_values", [])

            # Find the market value for this date
            market_value = 0.0
            for mv_entry in monthly_values:
                entry_date = date.fromisoformat(mv_entry["date"])
                if entry_date == date_point:
                    mv = mv_entry.get("market_value")
                    if mv is not None:
                        # Apply ownership percentage
                        ownership = _get_ownership_at_date(prop, date_point)
                        market_value = mv * ownership
                    break

            # Add to the exposure for this property type
            ptype = prop.property_type
            type_values[ptype] += market_value
            total_value += market_value

        # Store the absolute values for percentage calculation
        for ptype in property_types:
            exposure_by_type[ptype][date_point] = type_values[ptype]

    # Build the response data structure with both percentages and absolute values
    data = []
    for date_point in quarter_end_dates:
        # Calculate total at this date
        total = sum(exposure_by_type[ptype].get(date_point, 0.0) for ptype in property_types)

        row = {"date": date_point.isoformat()}
        if total > 0:
            # Calculate percentages and store absolute values
            for ptype in property_types:
                absolute_value = exposure_by_type[ptype].get(date_point, 0.0)
                percentage = (absolute_value / total) * 100
                row[ptype] = {
                    "percentage": round(percentage, 2),
                    "market_value": round(absolute_value, 2)
                }
        else:
            # If no total value, set to 0
            for ptype in property_types:
                row[ptype] = {
                    "percentage": 0.0,
                    "market_value": 0.0
                }

        data.append(row)

    return {
        "dates": [d.isoformat() for d in quarter_end_dates],
        "property_types": property_types,
        "data": data
    }


def _get_ownership_at_date(prop: Property, date_point: date) -> float:
    """
    Get the ownership percentage for a property at a specific date,
    considering ownership events.
    """
    if not prop.ownership_events:
        return prop.ownership_percent or 1.0

    # Find the applicable ownership event for this date
    applicable_ownership = prop.ownership_percent or 1.0
    for event in sorted(prop.ownership_events, key=lambda e: e.event_date):
        if event.event_date <= date_point:
            applicable_ownership = event.ownership_percent
        else:
            break

    return applicable_ownership


def get_portfolio_transactions(portfolio_id: int) -> List[Dict[str, object]]:
    """
    Get all acquisitions and dispositions for properties in a portfolio
    within the analysis period.

    Returns a list of transaction dicts with:
    - transaction_date
    - property_name
    - property_type
    - transaction_type ('acquisition' or 'disposition')
    - transaction_price
    """
    portfolio = Portfolio.query.get(portfolio_id)
    if not portfolio or not portfolio.analysis_start_date or not portfolio.analysis_end_date:
        return []

    properties = Property.query.filter_by(portfolio_id=portfolio_id).all()
    if not properties:
        return []

    transactions = []
    start_date = portfolio.analysis_start_date
    end_date = portfolio.analysis_end_date

    for prop in properties:
        # Add acquisition transaction if within analysis period
        if prop.purchase_date and start_date <= prop.purchase_date <= end_date:
            transactions.append({
                "transaction_date": prop.purchase_date.isoformat(),
                "property_name": prop.property_name,
                "property_type": prop.property_type,
                "transaction_type": "acquisition",
                "transaction_price": prop.purchase_price or 0.0
            })

        # Add disposition transaction if within analysis period
        if prop.exit_date and start_date <= prop.exit_date <= end_date:
            # Calculate market value at exit date for disposition price
            valuation = calculate_property_valuation(prop)
            monthly_values = valuation.get("monthly_market_values", [])

            exit_market_value = 0.0
            exit_month = _month_end(prop.exit_date)
            for mv_entry in monthly_values:
                entry_date = date.fromisoformat(mv_entry["date"])
                if entry_date == exit_month:
                    mv = mv_entry.get("market_value")
                    if mv is not None:
                        exit_market_value = mv
                    break

            transactions.append({
                "transaction_date": prop.exit_date.isoformat(),
                "property_name": prop.property_name,
                "property_type": prop.property_type,
                "transaction_type": "disposition",
                "transaction_price": exit_market_value
            })

    # Sort by transaction date
    transactions.sort(key=lambda x: x["transaction_date"])

    return transactions
