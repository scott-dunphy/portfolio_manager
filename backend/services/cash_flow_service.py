from __future__ import annotations

import json
import math
from calendar import monthrange
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional

from dateutil.relativedelta import relativedelta

from database import db
from models import CashFlow, Loan, Portfolio, Property
from services.sofr_client import get_forward_rate
from services.forward_curve_service import get_forward_treasury_rate


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
    portfolio = _get_loan_portfolio(loan_obj)
    auto_refi_enabled = bool(getattr(portfolio, 'auto_refinance_enabled', False)) if portfolio else False
    refi_spreads = _load_refi_spreads(portfolio) if auto_refi_enabled else {}
    property_obj = _resolve_property_for_loan(loan_obj)

    principal = _safe_float(loan_obj.principal_amount)
    rate = _safe_float(loan_obj.interest_rate) or 0.0
    start_date = _month_end(loan_obj.origination_date)
    maturity_date = _month_end(loan_obj.maturity_date)

    if principal is None or not start_date:
        return flows

    origination_fee_rate = _safe_float(getattr(loan_obj, 'origination_fee', None)) or 0.0

    # Initial funding is a cash outflow from the portfolio's perspective.
    flows.append(
        {
            "date": start_date,
            "type": "loan_funding",
            "amount": principal,
            "description": "Loan funded",
        }
    )

    origination_fee_amount = (principal or 0.0) * origination_fee_rate
    if origination_fee_amount:
        flows.append(
            {
                "date": start_date,
                "type": "loan_origination_fee",
                "amount": -abs(origination_fee_amount),
                "description": "Loan origination fee",
            }
        )

    if not maturity_date or maturity_date <= start_date:
        return flows

    sale_payoff_date = _determine_sale_payoff_date(property_obj, start_date, maturity_date)
    payoff_date = sale_payoff_date or maturity_date

    frequency = (loan_obj.payment_frequency or "monthly").lower()
    months_per_period = {"monthly": 1, "quarterly": 3, "annually": 12}.get(frequency, 1)

    if payoff_date > start_date:
        total_months = max(
            1,
            (payoff_date.year - start_date.year) * 12 + (payoff_date.month - start_date.month),
        )
        periods = max(1, math.ceil(total_months / months_per_period))
    else:
        total_months = 0
        periods = 0
    amortization_months = loan_obj.amortization_period_months or total_months
    io_months = loan_obj.io_period_months or 0
    rate_type = (getattr(loan_obj, 'rate_type', 'fixed') or 'fixed').lower()
    is_floating = rate_type == 'floating'
    sofr_spread = _safe_float(getattr(loan_obj, 'sofr_spread', 0.0)) or 0.0
    day_count_method = _normalize_day_count(getattr(loan_obj, 'interest_day_count', None))
    amortization_fraction = months_per_period / 12.0
    exit_fee = _safe_float(getattr(loan_obj, 'exit_fee', None)) or 0.0
    manual_overrides = _group_manual_loan_entries(loan_obj)

    if is_floating:
        full_interest_only = True
        io_periods = periods
        amortization_periods = periods
        fixed_periodic_rate = 0.0
        payment = 0.0
    else:
        periodic_rate = rate * amortization_fraction
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
    prev_payment_date = start_date
    for period_index in range(1, periods + 1):
        scheduled_date = start_date + relativedelta(months=months_per_period * period_index)
        payment_date = _month_end(min(scheduled_date, payoff_date))
        override_key = (payment_date.year, payment_date.month) if payment_date else None
        manual_entry = manual_overrides.pop(override_key, None) if override_key else None
        entry_payment_date = manual_entry['date'] if manual_entry else payment_date
        accrual_fraction = _day_count_fraction(prev_payment_date, payment_date, day_count_method, amortization_fraction)

        if is_floating:
            forward_rate = get_forward_rate(payment_date) or rate
            annual_rate = (forward_rate or 0.0) + sofr_spread
            interest = balance * annual_rate * accrual_fraction
        else:
            periodic_rate = fixed_periodic_rate
            interest_rate_for_period = rate * accrual_fraction
            interest = balance * interest_rate_for_period

        if full_interest_only or period_index <= io_periods:
            principal_component = 0.0
        else:
            principal_component = payment - interest if periodic_rate else payment
            if principal_component < 0:
                principal_component = 0.0

        manual_interest = None
        manual_principal = None
        if manual_entry:
            manual_interest = manual_entry.get('interest')
            manual_principal = manual_entry.get('principal')
            if manual_interest is not None:
                interest = manual_interest
            if manual_principal is not None:
                principal_component = manual_principal

        if principal_component > balance:
            principal_component = balance

        balance = max(0.0, balance - principal_component)

        if interest:
            flows.append(
                {
                    "date": entry_payment_date,
                    "type": "loan_interest",
                    "amount": -abs(interest),
                    "description": "Interest payment",
                }
            )
        if principal_component:
            flows.append(
                {
                    "date": entry_payment_date,
                    "type": "loan_principal",
                    "amount": -abs(principal_component),
                    "description": "Principal repayment",
                }
            )

        if balance <= 1e-4:
            break
        prev_payment_date = payment_date

    # Ensure the final balance is cleared (for balloons / interest-only structures).
    refi_balance = 0.0
    if balance > 1e-4:
        flows.append(
            {
                "date": payoff_date,
                "type": "loan_principal",
                "amount": -balance,
                "description": "Balloon repayment",
            }
        )
        if sale_payoff_date is None:
            refi_balance = balance
        balance = 0.0

    if auto_refi_enabled and refi_balance > 1e-4:
        refi_flows = _build_auto_refi_flows(
            refi_balance,
            maturity_date,
            property_obj,
            refi_spreads,
        )
        flows.extend(refi_flows)
    elif exit_fee:
        flows.append(
            {
                "date": payoff_date,
                "type": "loan_exit_fee",
                "amount": -abs(exit_fee),
                "description": "Loan exit fee",
            }
        )

    return flows


def _group_manual_loan_entries(loan_obj: Loan) -> Dict[tuple, dict]:
    manual_entries: Dict[tuple, dict] = {}
    entries = getattr(loan_obj, "manual_cash_flows", None) or []
    for entry in entries:
        payment_date = getattr(entry, "payment_date", None)
        if not payment_date:
            continue
        key = (payment_date.year, payment_date.month)
        manual_entries[key] = {
            "interest": _safe_float(getattr(entry, "interest_amount", None)),
            "principal": _safe_float(getattr(entry, "principal_amount", None)),
            "date": payment_date,
        }
    return manual_entries


def _determine_sale_payoff_date(
    property_obj: Optional[Property],
    start_date: Optional[date],
    maturity_date: Optional[date],
) -> Optional[date]:
    if not property_obj or not getattr(property_obj, 'exit_date', None):
        return None
    if not start_date or not maturity_date:
        return None
    candidate = _month_end(property_obj.exit_date)
    if not candidate:
        return None
    if candidate >= maturity_date:
        return None
    if candidate <= start_date:
        return start_date
    return candidate


def _interpolated_exit_cap_rate(
    property_obj: Property,
    target_date: date,
    portfolio: Optional[Portfolio],
) -> Optional[float]:
    exit_cap_target = _safe_float(property_obj.exit_cap_rate)
    if exit_cap_target is None or exit_cap_target <= 0:
        return None

    analysis_start = None
    if portfolio and portfolio.analysis_start_date:
        analysis_start = _month_end(portfolio.analysis_start_date)
    if not analysis_start:
        analysis_start = _month_end(_resolve_property_start_date(property_obj)) or target_date

    sale_anchor = (
        _month_end(property_obj.exit_date)
        if property_obj.exit_date
        else (_month_end(portfolio.analysis_end_date) if portfolio and portfolio.analysis_end_date else target_date)
    )
    if not sale_anchor or sale_anchor <= analysis_start:
        sale_anchor = target_date

    start_cap = _get_year1_cap_rate(property_obj)
    if start_cap is None:
        start_cap = exit_cap_target

    total_months = max(1, _months_between(analysis_start, sale_anchor))
    elapsed = max(0, min(_months_between(analysis_start, target_date), total_months))
    t = min(1.0, elapsed / total_months)
    return start_cap + (exit_cap_target - start_cap) * t


def _get_year1_cap_rate(property_obj: Property) -> Optional[float]:
    existing = _safe_float(getattr(property_obj, 'year_1_cap_rate', None))
    if existing is not None and existing > 0:
        return existing
    forward_noi = _safe_float(getattr(property_obj, 'initial_noi', None))
    market_value = _safe_float(getattr(property_obj, 'market_value_start', None))
    if forward_noi and market_value and market_value > 0:
        return forward_noi / market_value
    return None


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def _estimate_sale_amount(
    property_obj: Property,
    sale_date: date,
    initial_noi: Optional[float],
    noi_growth: float,
) -> Optional[float]:
    override_price = _safe_float(getattr(property_obj, 'disposition_price_override', None))
    if override_price is not None:
        return override_price
    if initial_noi is None:
        return _safe_float(property_obj.purchase_price)

    start_date = _month_end(_resolve_property_start_date(property_obj))
    portfolio = _get_property_portfolio(property_obj)
    if portfolio and portfolio.analysis_start_date:
        start_date = _month_end(portfolio.analysis_start_date)
    if not start_date:
        return _safe_float(property_obj.purchase_price)

    projected_noi = _forward_noi_for_sale(property_obj, sale_date, initial_noi, noi_growth, start_date)
    if projected_noi is None:
        return _safe_float(property_obj.purchase_price)

    exit_cap = _interpolated_exit_cap_rate(property_obj, sale_date, portfolio)
    if exit_cap is None or exit_cap <= 0:
        return _safe_float(property_obj.purchase_price)

    return projected_noi / exit_cap if exit_cap else None


def _forward_noi_for_sale(
    property_obj: Property,
    sale_date: date,
    initial_noi: Optional[float],
    noi_growth: float,
    start_anchor: date,
) -> Optional[float]:
    manual_entries = list(getattr(property_obj, "manual_cash_flows", []) or [])
    use_manual = bool(getattr(property_obj, "use_manual_noi_capex", False) and manual_entries)
    manual_by_month = {}
    manual_by_year = {}
    if use_manual:
        for entry in manual_entries:
            if entry.month:
                manual_by_month[(entry.year, entry.month)] = entry
            else:
                manual_by_year[entry.year] = entry

    total_noi = 0.0
    months_to_project = 12
    base_month = _month_end(sale_date)
    purchase_month = _month_end(getattr(property_obj, 'purchase_date', None))
    if not base_month:
        return None

    growth_base = _month_end(_resolve_property_start_date(property_obj)) or start_anchor

    current_month = _month_end(base_month + relativedelta(months=1))
    for _ in range(months_to_project):
        if current_month is None:
            break
        manual_value = None
        if use_manual:
            manual_month_entry = manual_by_month.get((current_month.year, current_month.month))
            if manual_month_entry:
                manual_value = manual_month_entry.annual_noi or 0.0
            else:
                manual_entry = manual_by_year.get(current_month.year)
                if manual_entry and manual_entry.annual_noi is not None:
                    manual_value = (manual_entry.annual_noi or 0.0) / 12.0
        if manual_value is not None:
            monthly_noi = manual_value
        elif purchase_month and current_month < purchase_month:
            monthly_noi = 0.0
        else:
            if initial_noi is None:
                monthly_noi = 0.0
            else:
                months_since_start = max(
                    0,
                    (current_month.year - growth_base.year) * 12
                    + (current_month.month - growth_base.month)
                )
                full_years_elapsed = (months_since_start - 1) // 12 if months_since_start > 0 else 0
                annual_noi = initial_noi * ((1 + noi_growth) ** full_years_elapsed)
                monthly_noi = annual_noi / 12.0
        total_noi += monthly_noi
        current_month = _month_end(current_month + relativedelta(months=1))

    return total_noi


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


def _normalize_day_count(value: Optional[str]) -> str:
    normalized = (value or '30/360').lower().replace('_', '/')
    if normalized not in {'30/360', 'actual/360', 'actual/365'}:
        return '30/360'
    return normalized


def _day_count_fraction(
    start: Optional[date],
    end: Optional[date],
    method: str,
    fallback_fraction: float,
) -> float:
    if not start or not end or end <= start:
        return max(fallback_fraction, 1 / 12.0)

    if method == 'actual/360':
        days = (end - start).days
        return days / 360.0
    if method == 'actual/365':
        days = (end - start).days
        return days / 365.0

    # 30/360 US convention.
    y1, m1, d1 = start.year, start.month, min(start.day, 30)
    y2, m2, d2 = end.year, end.month, min(end.day if start.day < 30 else 30, 30)
    fraction = ((y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)) / 360.0
    if fraction <= 0:
        return max(fallback_fraction, 1 / 12.0)
    return fraction


def _get_loan_portfolio(loan_obj: Loan) -> Optional[Portfolio]:
    portfolio = getattr(loan_obj, 'portfolio', None)
    if portfolio is not None:
        return portfolio
    if loan_obj.portfolio_id:
        return Portfolio.query.get(loan_obj.portfolio_id)
    return None


def _resolve_property_for_loan(loan_obj: Loan) -> Optional[Property]:
    property_obj = getattr(loan_obj, 'property', None)
    if property_obj is not None:
        return property_obj
    if loan_obj.property_id:
        return Property.query.get(loan_obj.property_id)
    return None


def _load_refi_spreads(portfolio: Optional[Portfolio]) -> Dict[str, float]:
    if not portfolio or not getattr(portfolio, 'auto_refinance_spreads', None):
        return {}
    try:
        data = json.loads(portfolio.auto_refinance_spreads)
        if isinstance(data, dict):
            spreads: Dict[str, float] = {}
            for key, value in data.items():
                if value is None:
                    continue
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                # Spreads are stored in basis points on the portfolio form.
                spreads[str(key).strip().lower()] = numeric / 10000.0
            return spreads
    except (json.JSONDecodeError, ValueError, TypeError):
        return {}
    return {}


def _get_spread_for_property(spreads: Dict[str, float], property_obj: Optional[Property]) -> float:
    type_key = None
    if property_obj and property_obj.property_type:
        type_key = property_obj.property_type.strip().lower()
    elif not property_obj:
        type_key = 'unassigned'
    if type_key and type_key in spreads:
        return spreads[type_key]
    return spreads.get('default', 0.0)


def _build_auto_refi_flows(
    balance: float,
    maturity_date: date,
    property_obj: Optional[Property],
    refi_spreads: Dict[str, float],
) -> List[dict]:
    if balance <= 0:
        return []
    spread = _get_spread_for_property(refi_spreads, property_obj)
    forward_rate = get_forward_treasury_rate(maturity_date) or 0.0
    total_rate = forward_rate + spread
    if total_rate < 0:
        total_rate = 0.0
    forward_pct = forward_rate * 100.0
    spread_pct = spread * 100.0

    flows = []
    term_months = 120  # 10-year, monthly periods
    start_date = maturity_date
    flows.append(
        {
            "date": start_date,
            "type": "loan_funding",
            "amount": balance,
            "description": "Auto-refinance funding",
        }
    )

    for month_index in range(1, term_months + 1):
        payment_date = _month_end(start_date + relativedelta(months=month_index))
        interest = -balance * (total_rate / 12.0)
        flows.append(
            {
                "date": payment_date,
                "type": "loan_interest",
                "amount": interest,
                "description": f"Auto-refinance interest (10y {forward_pct:.2f}%, spread {spread_pct:.2f}%)",
            }
        )

    final_date = _month_end(start_date + relativedelta(months=term_months))
    flows.append(
        {
            "date": final_date,
            "type": "loan_principal",
            "amount": -balance,
            "description": "Auto-refinance maturity",
        }
    )

    return flows
