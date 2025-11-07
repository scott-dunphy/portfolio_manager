from __future__ import annotations

import math
from calendar import monthrange
from datetime import date, datetime
from typing import Iterable, List, Optional

from dateutil.relativedelta import relativedelta

from database import db
from models import CashFlow, Loan, Portfolio, Property
from services.sofr_client import get_forward_rate


def regenerate_property_cash_flows(property_obj: Property, commit: bool = True) -> int:
    """
    Rebuild the cash flows associated with a property using simple NOI projections.

    Returns the number of cash flow rows created.
    """
    if not property_obj:
        return 0

    _delete_cash_flows(property_id=property_obj.id, commit=False)
    flows = _build_property_cash_flows(property_obj)

    if flows:
        db.session.add_all(
            [
                CashFlow(
                    portfolio_id=property_obj.portfolio_id,
                    property_id=property_obj.id,
                    loan_id=None,
                    date=flow["date"],
                    cash_flow_type=flow["type"],
                    amount=flow["amount"],
                    description=flow["description"],
                )
                for flow in flows
            ]
        )

    if commit:
        db.session.commit()

    return len(flows)


def regenerate_loan_cash_flows(loan_obj: Loan, commit: bool = True) -> int:
    """
    Rebuild the cash flows associated with a loan using a vanilla amortisation schedule.

    Returns the number of cash flow rows created.
    """
    if not loan_obj:
        return 0

    _delete_cash_flows(property_id=None, loan_id=loan_obj.id, commit=False)
    flows = _build_loan_cash_flows(loan_obj)

    if flows:
        db.session.add_all(
            [
                CashFlow(
                    portfolio_id=loan_obj.portfolio_id,
                    property_id=loan_obj.property_id,
                    loan_id=loan_obj.id,
                    date=flow["date"],
                    cash_flow_type=flow["type"],
                    amount=flow["amount"],
                    description=flow["description"],
                )
                for flow in flows
            ]
        )

    if commit:
        db.session.commit()

    return len(flows)


def clear_property_cash_flows(property_id: int, commit: bool = True) -> None:
    _delete_cash_flows(property_id=property_id, commit=commit)


def clear_loan_cash_flows(loan_id: int, commit: bool = True) -> None:
    _delete_cash_flows(loan_id=loan_id, commit=commit)


# Internal helpers ----------------------------------------------------------------

def _delete_cash_flows(
    property_id: Optional[int] = None,
    loan_id: Optional[int] = None,
    commit: bool = True,
) -> None:
    query = CashFlow.query
    if property_id is not None:
        query = query.filter_by(property_id=property_id)
    if loan_id is not None:
        query = query.filter_by(loan_id=loan_id)

    query.delete(synchronize_session=False)
    if commit:
        db.session.commit()


def _build_property_cash_flows(property_obj: Property) -> List[dict]:
    flows: List[dict] = []

    purchase_month_end = _month_end(property_obj.purchase_date)
    start_anchor = _resolve_property_start_date(property_obj)
    start_date = _month_end(start_anchor)
    end_date = _month_end(property_obj.exit_date) if property_obj.exit_date else None

    if purchase_month_end and property_obj.purchase_price:
        flows.append(
            {
                "date": purchase_month_end,
                "type": "property_acquisition",
                "amount": -float(property_obj.purchase_price),
                "description": "Property acquisition cost",
            }
        )

    initial_noi = _safe_float(property_obj.initial_noi)
    noi_growth = _safe_float(property_obj.noi_growth_rate) or 0.0
    capex_pct = _safe_float(getattr(property_obj, 'capex_percent_of_noi', None)) or 0.0
    manual_entries = list(getattr(property_obj, "manual_cash_flows", []) or [])
    use_manual = bool(getattr(property_obj, "use_manual_noi_capex", False)) and bool(manual_entries)
    manual_by_year = {}
    manual_by_month = {}
    if use_manual:
        for entry in manual_entries:
            if entry.month:
                manual_by_month[(entry.year, entry.month)] = entry
            else:
                manual_by_year[entry.year] = entry

    # Generate ongoing NOI/capex cash flows.
    if start_date and (initial_noi is not None or use_manual):
        projected_end = end_date or _month_end(start_date + relativedelta(years=5))
        if projected_end < start_date:
            projected_end = start_date

        for idx, month in enumerate(_iter_months(start_date, projected_end)):
            if use_manual:
                manual_month_entry = manual_by_month.get((month.year, month.month))
                if manual_month_entry:
                    monthly_noi = manual_month_entry.annual_noi or 0.0
                    monthly_capex = manual_month_entry.annual_capex or 0.0
                else:
                    manual_entry = manual_by_year.get(month.year)
                    monthly_noi = (
                        (manual_entry.annual_noi or 0.0) / 12.0
                        if manual_entry and manual_entry.annual_noi is not None
                        else 0.0
                    )
                    monthly_capex = (
                        (manual_entry.annual_capex or 0.0) / 12.0
                        if manual_entry and manual_entry.annual_capex is not None
                        else 0.0
                    )
            else:
                years_elapsed = idx // 12
                annual_noi = (
                    initial_noi * ((1 + noi_growth) ** years_elapsed)
                    if initial_noi is not None
                    else 0.0
                )
                monthly_noi = annual_noi / 12.0
                monthly_capex = monthly_noi * capex_pct

            if monthly_noi:
                flows.append(
                    {
                        "date": month,
                        "type": "property_noi",
                        "amount": monthly_noi,
                        "description": "Projected NOI",
                    }
                )
            if monthly_capex:
                flows.append(
                    {
                        "date": month,
                        "type": "property_capex",
                        "amount": -abs(monthly_capex),
                        "description": "Projected Capex",
                    }
                )

    if end_date:
        sale_amount = _estimate_sale_amount(property_obj, end_date, initial_noi, noi_growth)
        if sale_amount is not None:
            flows.append(
                {
                    "date": end_date,
                    "type": "property_sale",
                    "amount": sale_amount,
                    "description": "Projected sale proceeds",
                }
            )

    return flows


def _build_loan_cash_flows(loan_obj: Loan) -> List[dict]:
    flows: List[dict] = []

    principal = _safe_float(loan_obj.principal_amount)
    rate = _safe_float(loan_obj.interest_rate) or 0.0
    start_date = _month_end(loan_obj.origination_date)
    maturity_date = _month_end(loan_obj.maturity_date)

    if principal is None or not start_date:
        return flows

    # Initial funding is a cash outflow from the portfolio's perspective.
    flows.append(
        {
            "date": start_date,
            "type": "loan_funding",
            "amount": principal,
            "description": "Loan funded",
        }
    )

    if not maturity_date or maturity_date <= start_date:
        return flows

    frequency = (loan_obj.payment_frequency or "monthly").lower()
    months_per_period = {"monthly": 1, "quarterly": 3, "annually": 12}.get(frequency, 1)

    total_months = max(
        1,
        (maturity_date.year - start_date.year) * 12 + (maturity_date.month - start_date.month),
    )
    periods = max(1, math.ceil(total_months / months_per_period))
    amortization_months = loan_obj.amortization_period_months or total_months
    io_months = loan_obj.io_period_months or 0
    rate_type = (getattr(loan_obj, 'rate_type', 'fixed') or 'fixed').lower()
    is_floating = rate_type == 'floating'
    sofr_spread = _safe_float(getattr(loan_obj, 'sofr_spread', 0.0)) or 0.0

    if is_floating:
        full_interest_only = True
        io_periods = periods
        amortization_periods = periods
        fixed_periodic_rate = 0.0
        payment = 0.0
    else:
        periodic_rate = rate * months_per_period / 12.0
        full_interest_only = (
            (loan_obj.amortization_period_months in (None, 0))
            and (io_months in (None, 0))
        )
        amortization_periods = max(1, math.ceil(amortization_months / months_per_period))
        io_periods = math.ceil(io_months / months_per_period) if io_months else 0
        if full_interest_only:
            payment = principal * periodic_rate  # interest-only, principal handled separately
        elif periodic_rate == 0:
            payment = principal / amortization_periods
        else:
            payment = principal * (periodic_rate) / (1 - (1 + periodic_rate) ** (-amortization_periods))
        fixed_periodic_rate = periodic_rate

    balance = principal
    for period_index in range(1, periods + 1):
        scheduled_date = start_date + relativedelta(months=months_per_period * period_index)
        payment_date = _month_end(min(scheduled_date, maturity_date))

        if is_floating:
            forward_rate = get_forward_rate(payment_date) or rate
            annual_rate = (forward_rate or 0.0) + sofr_spread
            periodic_rate = annual_rate * months_per_period / 12.0
        else:
            periodic_rate = fixed_periodic_rate

        interest = balance * periodic_rate

        if full_interest_only or period_index <= io_periods:
            principal_component = 0.0
        else:
            principal_component = payment - interest if periodic_rate else payment

        if principal_component > balance:
            principal_component = balance

        balance = max(0.0, balance - principal_component)

        if interest:
            flows.append(
                {
                    "date": payment_date,
                    "type": "loan_interest",
                    "amount": -interest,
                    "description": "Interest payment",
                }
            )
        if principal_component:
            flows.append(
                {
                    "date": payment_date,
                    "type": "loan_principal",
                    "amount": -principal_component,
                    "description": "Principal repayment",
                }
            )

        if balance <= 1e-4:
            break

    # Ensure the final balance is cleared (for balloons / interest-only structures).
    if balance > 1e-4:
        flows.append(
            {
                "date": maturity_date,
                "type": "loan_principal",
                "amount": -balance,
                "description": "Balloon repayment",
            }
        )

    return flows


def _estimate_sale_amount(
    property_obj: Property,
    sale_date: date,
    initial_noi: Optional[float],
    noi_growth: float,
) -> Optional[float]:
    if initial_noi is None:
        return _safe_float(property_obj.purchase_price)

    exit_cap = _safe_float(property_obj.exit_cap_rate)
    if exit_cap is None or exit_cap <= 0:
        return _safe_float(property_obj.purchase_price)

    start_date = _month_end(_resolve_property_start_date(property_obj))
    if not start_date:
        baseline_price = _safe_float(property_obj.purchase_price)
        return baseline_price

    years_elapsed = max(0, (sale_date.year - start_date.year) + (sale_date.month - start_date.month) / 12.0)
    projected_noi = initial_noi * ((1 + noi_growth) ** years_elapsed)
    return projected_noi / exit_cap if exit_cap else None


def _month_end(value: Optional[date]) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.date()
    last_day = monthrange(value.year, value.month)[1]
    return value.replace(day=last_day)


def _iter_months(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current = _month_end(current + relativedelta(months=1))


def _safe_float(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_property_start_date(property_obj: Property) -> Optional[date]:
    if property_obj.purchase_date:
        return property_obj.purchase_date

    portfolio = _get_property_portfolio(property_obj)
    if portfolio and portfolio.analysis_start_date:
        return portfolio.analysis_start_date

    return None


def _get_property_portfolio(property_obj: Property) -> Optional[Portfolio]:
    portfolio = getattr(property_obj, "portfolio", None)
    if portfolio is not None:
        return portfolio

    if property_obj.portfolio_id:
        return Portfolio.query.get(property_obj.portfolio_id)

    return None
