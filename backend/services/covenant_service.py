from __future__ import annotations

from collections import defaultdict, deque
from datetime import date
from typing import Deque, Dict, List, Optional, Tuple

from dateutil.relativedelta import relativedelta
from sqlalchemy import func

from database import db
from models import CashFlow, Loan, Portfolio, Property
from services.property_valuation_service import calculate_property_valuation

MONTHS_IN_TTM = 12


def build_covenant_metrics(portfolio_id: int, apply_ownership: bool = False) -> Dict[str, object]:
    portfolio: Portfolio = Portfolio.query.get_or_404(portfolio_id)
    if not portfolio.analysis_start_date or not portfolio.analysis_end_date:
        raise ValueError("Portfolio is missing analysis dates.")

    analysis_start = _month_end(portfolio.analysis_start_date)
    analysis_end = _month_end(portfolio.analysis_end_date)

    min_required_start = _month_end(analysis_start + relativedelta(months=-(MONTHS_IN_TTM - 1)))
    earliest_flow_date = (
        db.session.query(func.min(CashFlow.date))
        .filter(
            CashFlow.portfolio_id == portfolio_id,
            CashFlow.cash_flow_type.in_(['property_noi', 'loan_interest', 'loan_principal'])
        )
        .scalar()
    )
    if earliest_flow_date:
        earliest_available_start = _month_end(earliest_flow_date)
        ttm_start = min(min_required_start, earliest_available_start)
    else:
        ttm_start = min_required_start

    properties: List[Property] = Property.query.filter_by(portfolio_id=portfolio_id).all()
    property_map: Dict[int, Property] = {prop.id: prop for prop in properties}
    ownership_lookup = _prepare_ownership_lookup(properties)
    property_valuations = _prepare_property_valuations(properties, apply_ownership)

    loans: List[Loan] = Loan.query.filter_by(portfolio_id=portfolio_id).all()

    cash_flows: List[CashFlow] = (
        CashFlow.query.filter(
            CashFlow.portfolio_id == portfolio_id,
            CashFlow.date >= ttm_start,
            CashFlow.date <= analysis_end,
        )
        .order_by(CashFlow.date)
        .all()
    )
    loan_flows_all: List[CashFlow] = (
        CashFlow.query.filter(
            CashFlow.portfolio_id == portfolio_id,
            CashFlow.loan_id.isnot(None),
            CashFlow.date <= analysis_end,
        )
        .order_by(CashFlow.date)
        .all()
    )

    month_list = _iter_months(ttm_start, analysis_end)
    month_list_analysis = [month for month in month_list if month >= analysis_start]

    property_noi = _collect_property_noi(cash_flows)
    loan_cash_flows_full = _collect_loan_cash_flows(loan_flows_all)
    loan_balances = _calculate_loan_balances(loans, loan_cash_flows_full, month_list)
    loan_cash_flows_ttm = _collect_loan_cash_flows(cash_flows)
    loan_debt_service = _summarize_loan_debt_service(loan_cash_flows_ttm)

    loan_groups = defaultdict(list)
    for loan in loans:
        key = loan.property_id
        loan_groups[key].append(loan.id)

    property_metrics = _calculate_property_metrics(
        month_list,
        property_map,
        property_noi,
        loan_balances,
        loan_debt_service,
        property_valuations,
        ownership_lookup,
        apply_ownership,
        loan_groups,
    )

    unassigned_metrics = _calculate_unassigned_debt_metrics(
        month_list,
        loan_groups.get(None, []),
        loan_debt_service,
        loan_balances,
    )

    fund_metrics = _calculate_fund_metrics(
        month_list,
        property_metrics,
        unassigned_metrics,
    )

    months_payload = []
    for month in month_list_analysis:
        fund = fund_metrics.get(month, {})
        properties_payload = [
            metrics for metrics in property_metrics.get(month, {}).values()
            if metrics.get('has_data')
        ]
        properties_payload.sort(key=lambda item: item['property_name'])
        months_payload.append(
            {
                'date': month.isoformat(),
                'fund': _format_metric_payload(fund),
                'properties': [_format_metric_payload(entry) for entry in properties_payload],
            }
        )

    return {
        'portfolio_id': portfolio_id,
        'analysis_start_date': portfolio.analysis_start_date.isoformat(),
        'analysis_end_date': portfolio.analysis_end_date.isoformat(),
        'months': months_payload,
    }


def _calculate_property_metrics(
    month_list: List[date],
    property_map: Dict[int, Property],
    property_noi: Dict[int, Dict[date, float]],
    loan_balances: Dict[int, Dict[date, float]],
    loan_debt_service: Dict[int, Dict[date, float]],
    property_valuations: Dict[int, Dict[date, float]],
    ownership_lookup: Dict[int, List[Tuple[date, float]]],
    apply_ownership: bool,
    loan_groups: Dict[Optional[int], List[int]],
) -> Dict[date, Dict[int, dict]]:
    metrics_by_month = defaultdict(dict)
    noi_windows: Dict[int, Deque[Tuple[date, float]]] = defaultdict(deque)
    debt_windows: Dict[int, Deque[Tuple[date, float]]] = defaultdict(deque)
    noi_sums: Dict[int, float] = defaultdict(float)
    debt_sums: Dict[int, float] = defaultdict(float)

    for month in month_list:
        for prop_id, prop in property_map.items():
            month_noi = property_noi.get(prop_id, {}).get(month, 0.0)
            if apply_ownership:
                percent = _ownership_percent(
                    ownership_lookup.get(prop_id, []),
                    month,
                    default=prop.ownership_percent or 1.0
                )
                month_noi *= percent

            _update_window(noi_windows[prop_id], noi_sums, prop_id, month, month_noi)
            _trim_window(noi_windows[prop_id], noi_sums, prop_id, month)

            debt_service_month = _property_debt_service_for_month(
                prop_id,
                month,
                loan_debt_service,
                loan_groups,
            )
            if apply_ownership:
                percent = _ownership_percent(
                    ownership_lookup.get(prop_id, []),
                    month,
                    default=prop.ownership_percent or 1.0
                )
                debt_service_month *= percent

            _update_window(debt_windows[prop_id], debt_sums, prop_id, month, debt_service_month)
            _trim_window(debt_windows[prop_id], debt_sums, prop_id, month)

            outstanding = _property_outstanding_for_month(
                prop_id,
                month,
                loan_balances,
                apply_ownership,
                ownership_lookup,
                property_map,
                loan_groups,
            )

            ttm_noi = noi_sums.get(prop_id, 0.0)
            ttm_debt_service = debt_sums.get(prop_id, 0.0)
            dscr = _safe_divide(ttm_noi, ttm_debt_service)
            valuation = property_valuations.get(prop_id, {}).get(month)
            if valuation is None:
                continue
            ltv = _safe_divide(outstanding, valuation)
            debt_yield = _safe_divide(ttm_noi, outstanding)

            metrics_by_month[month][prop_id] = {
                'property_id': prop_id,
                'property_name': prop.property_name or prop.property_id,
                'ttm_noi': ttm_noi,
                'ttm_debt_service': ttm_debt_service,
                'outstanding_debt': outstanding,
                'market_value': valuation,
                'dscr': dscr,
                'ltv': ltv,
                'debt_yield': debt_yield,
                'has_data': bool(ttm_noi or ttm_debt_service or outstanding),
            }

    return metrics_by_month


def _calculate_fund_metrics(
    month_list: List[date],
    property_metrics: Dict[date, Dict[int, dict]],
    unassigned_metrics: Dict[date, dict],
) -> Dict[date, dict]:
    fund_metrics = {}
    for month in month_list:
        properties = property_metrics.get(month, {})
        total_noi = sum(entry.get('ttm_noi', 0.0) for entry in properties.values())
        total_debt_service = sum(entry.get('ttm_debt_service', 0.0) for entry in properties.values())
        total_outstanding = sum(entry.get('outstanding_debt', 0.0) for entry in properties.values())
        total_value = sum(entry.get('market_value', 0.0) for entry in properties.values())

        total_debt_service += unassigned_metrics.get(month, {}).get('ttm_debt_service', 0.0)
        total_outstanding += unassigned_metrics.get(month, {}).get('outstanding', 0.0)

        dscr = _safe_divide(total_noi, total_debt_service)
        ltv = _safe_divide(total_outstanding, total_value)
        debt_yield = _safe_divide(total_noi, total_outstanding)

        fund_metrics[month] = {
            'ttm_noi': total_noi,
            'ttm_debt_service': total_debt_service,
            'outstanding_debt': total_outstanding,
            'market_value': total_value,
            'dscr': dscr,
            'ltv': ltv,
            'debt_yield': debt_yield,
            'has_data': True,
        }

    return fund_metrics


def _collect_property_noi(cash_flows: List[CashFlow]) -> Dict[int, Dict[date, float]]:
    result = defaultdict(lambda: defaultdict(float))
    for cf in cash_flows:
        if not cf.property_id or not cf.date:
            continue
        if (cf.cash_flow_type or '').lower() != 'property_noi':
            continue
        result[cf.property_id][_month_end(cf.date)] += cf.amount or 0.0
    return result


def _collect_loan_cash_flows(cash_flows: List[CashFlow]) -> Dict[int, List[CashFlow]]:
    result = defaultdict(list)
    for cf in cash_flows:
        if not cf.loan_id:
            continue
        result[cf.loan_id].append(cf)
    for flows in result.values():
        flows.sort(key=lambda cf: (cf.date or date.min, cf.id or 0))
    return result


def _calculate_loan_balances(
    loans: List[Loan],
    loan_cash_flows: Dict[int, List[CashFlow]],
    month_list: List[date],
) -> Dict[int, Dict[date, float]]:
    balances = defaultdict(dict)
    for loan in loans:
        flows = loan_cash_flows.get(loan.id, [])
        pointer = 0
        balance = 0.0
        for month in month_list:
            while pointer < len(flows) and flows[pointer].date and flows[pointer].date <= month:
                cf = flows[pointer]
                flow_type = (cf.cash_flow_type or '').lower()
                amount = cf.amount or 0.0
                if flow_type == 'loan_funding':
                    balance += amount
                elif flow_type == 'loan_principal':
                    balance += amount
                pointer += 1
            balances[loan.id][month] = balance
    return balances


def _summarize_loan_debt_service(
    loan_cash_flows: Dict[int, List[CashFlow]]
) -> Dict[int, Dict[date, float]]:
    debt_service = defaultdict(lambda: defaultdict(float))
    for loan_id, flows in loan_cash_flows.items():
        for cf in flows:
            if not cf.date:
                continue
            flow_type = (cf.cash_flow_type or '').lower()
            if flow_type not in {'loan_interest', 'loan_principal'}:
                continue
            description = (cf.description or '').lower()
            if flow_type == 'loan_principal' and 'balloon repayment' in description:
                continue
            debt_service[loan_id][_month_end(cf.date)] += abs(cf.amount or 0.0)
    return debt_service


def _calculate_unassigned_debt_metrics(
    month_list: List[date],
    loan_ids: List[int],
    loan_debt_service: Dict[int, Dict[date, float]],
    loan_balances: Dict[int, Dict[date, float]],
) -> Dict[date, dict]:
    metrics = {}
    window = deque()
    running_total = 0.0
    for month in month_list:
        month_value = 0.0
        for loan_id in loan_ids:
            month_value += loan_debt_service.get(loan_id, {}).get(month, 0.0)
        window.append((month, month_value))
        running_total += month_value
        while window and (month - window[0][0]).days >= 365:
            running_total -= window.popleft()[1]
        outstanding = sum(loan_balances.get(loan_id, {}).get(month, 0.0) for loan_id in loan_ids)
        metrics[month] = {
            'ttm_debt_service': running_total,
            'outstanding': outstanding,
        }
    return metrics


def _property_debt_service_for_month(
    property_id: int,
    month: date,
    loan_debt_service: Dict[int, Dict[date, float]],
    loan_groups: Dict[Optional[int], List[int]],
) -> float:
    total = 0.0
    for loan_id in loan_groups.get(property_id, []):
        total += loan_debt_service.get(loan_id, {}).get(month, 0.0)
    return total


def _property_outstanding_for_month(
    property_id: int,
    month: date,
    loan_balances: Dict[int, Dict[date, float]],
    apply_ownership: bool,
    ownership_lookup: Dict[int, List[Tuple[date, float]]],
    property_map: Dict[int, Property],
    loan_groups: Dict[Optional[int], List[int]],
) -> float:
    total = 0.0
    for loan_id in loan_groups.get(property_id, []):
        balance = loan_balances.get(loan_id, {}).get(month, 0.0)
        total += balance
    if apply_ownership:
        property_obj = property_map.get(property_id)
        percent = _ownership_percent(
            ownership_lookup.get(property_id, []),
            month,
            default=property_obj.ownership_percent if property_obj else 1.0
        )
        total *= percent
    return total


def _update_window(
    window: Deque[Tuple[date, float]],
    sums: Dict[int, float],
    key: int,
    month: date,
    value: float,
):
    window.append((month, value))
    sums[key] += value


def _trim_window(
    window: Deque[Tuple[date, float]],
    sums: Dict[int, float],
    key: int,
    month: date,
):
    while window and (month - window[0][0]).days >= 365:
        old_month, old_value = window.popleft()
        sums[key] -= old_value


def _format_metric_payload(data: dict) -> dict:
    if not data:
        return {}
    payload = {
        'ttm_noi': round(data.get('ttm_noi') or 0.0, 2),
        'ttm_debt_service': round(data.get('ttm_debt_service') or 0.0, 2),
        'outstanding_debt': round(data.get('outstanding_debt') or 0.0, 2),
        'market_value': round(data.get('market_value') or 0.0, 2),
        'dscr': data.get('dscr'),
        'ltv': data.get('ltv'),
        'debt_yield': data.get('debt_yield'),
    }
    if 'property_id' in data:
        payload['property_id'] = data['property_id']
        payload['property_name'] = data.get('property_name')
    if 'has_data' in data:
        payload['has_data'] = data['has_data']
    return payload


def _safe_divide(numerator: float, denominator: float) -> Optional[float]:
    if denominator in (0, None):
        return None
    return numerator / denominator


def _prepare_property_valuations(properties: List[Property], apply_ownership: bool):
    lookup = {}
    for prop in properties:
        valuation = calculate_property_valuation(prop)
        entries = {}
        for item in valuation.get('monthly_market_values', []):
            date_str = item.get('date')
            if not date_str:
                continue
            entry_date = date.fromisoformat(date_str)
            value = item.get('market_value')
            if apply_ownership and value is not None:
                value *= prop.ownership_percent or 1.0
            entries[entry_date] = value
        lookup[prop.id] = entries
    return lookup


def _prepare_ownership_lookup(properties: List[Property]) -> Dict[int, List[Tuple[date, float]]]:
    lookup = {}
    for prop in properties:
        events = sorted(prop.ownership_events, key=lambda event: event.event_date or date.min)
        lookup[prop.id] = [(event.event_date, event.ownership_percent) for event in events]
    return lookup


def _ownership_percent(events: List[Tuple[date, float]], target_date: date, default: float = 1.0) -> float:
    percent = default or 1.0
    for event_date, value in events:
        if not event_date:
            continue
        if event_date <= target_date:
            percent = value
        else:
            break
    return percent


def _month_end(value: date) -> date:
    if hasattr(value, "date"):
        value = value.date()
    return (value.replace(day=1) + relativedelta(months=1, days=-1))


def _iter_months(start: date, end: date) -> List[date]:
    current = start
    months = []
    while current <= end:
        months.append(current)
        current = _month_end(current + relativedelta(months=1))
    return months
