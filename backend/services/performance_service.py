from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from calendar import monthrange
from typing import Dict, List, Optional, Tuple

from dateutil.relativedelta import relativedelta

from models import CashFlow, Portfolio, Property
from services.property_valuation_service import calculate_property_valuation


def build_quarterly_performance(portfolio_id: int, apply_ownership: bool = False) -> Dict[str, object]:
    portfolio: Portfolio = Portfolio.query.get_or_404(portfolio_id)

    if not portfolio.analysis_start_date or not portfolio.analysis_end_date:
        raise ValueError("Portfolio is missing analysis dates.")

    start_date = portfolio.analysis_start_date
    end_date = portfolio.analysis_end_date

    cash_flows: List[CashFlow] = (
        CashFlow.query.filter(
            CashFlow.portfolio_id == portfolio_id,
            CashFlow.date >= start_date,
            CashFlow.date <= end_date,
        )
        .order_by(CashFlow.date)
        .all()
    )

    properties: List[Property] = Property.query.filter_by(portfolio_id=portfolio_id).all()
    property_map = {prop.id: prop for prop in properties}
    ownership_lookup = _prepare_ownership_lookup(properties)
    property_states = _prepare_property_states(properties, apply_ownership)
    capex_by_property, sales_by_property = _accumulate_property_events(cash_flows)

    quarters: List[Dict[str, object]] = []
    running_nav = float(portfolio.beginning_nav or 0.0)

    flow_index = 0
    total_flows = len(cash_flows)

    period_start = start_date
    while period_start <= end_date:
        quarter_start = _quarter_start(period_start)
        quarter_end = _quarter_end(quarter_start)
        period_end = min(quarter_end, end_date)

        period_flows: List[CashFlow] = []

        while flow_index < total_flows and cash_flows[flow_index].date and cash_flows[flow_index].date < period_start:
            flow_index += 1

        lookahead = flow_index
        while (
            lookahead < total_flows
            and cash_flows[lookahead].date
            and cash_flows[lookahead].date <= period_end
        ):
            period_flows.append(cash_flows[lookahead])
            lookahead += 1
        flow_index = lookahead

        capital_calls = _sum_amounts(period_flows, {'capital_call'}, property_map, ownership_lookup, apply_ownership=apply_ownership)
        redemptions = _sum_amounts(period_flows, {'redemption', 'redemption_payment'}, property_map, ownership_lookup, absolute=True, apply_ownership=apply_ownership)
        noi = _sum_amounts(period_flows, {'property_noi'}, property_map, ownership_lookup, apply_ownership=apply_ownership)
        interest_expense = _sum_amounts(period_flows, {'loan_interest'}, property_map, ownership_lookup, absolute=True, apply_ownership=apply_ownership)

        property_flows = _summarize_property_flows(
            period_flows,
            property_map,
            ownership_lookup,
            apply_ownership,
        )

        property_details, appreciation_total = _calculate_appreciation_for_quarter(
            property_states,
            capex_by_property,
            sales_by_property,
            property_flows,
            period_end,
            _format_quarter_label(period_start),
            apply_ownership,
            property_map,
            ownership_lookup,
        )

        denominator = running_nav + capital_calls - redemptions
        income = noi - interest_expense
        total_return = income + appreciation_total
        twr = total_return / denominator if denominator else None
        ending_nav = denominator + total_return

        quarter_label = _format_quarter_label(period_start)

        quarters.append(
            {
                'label': quarter_label,
                'start_date': period_start.isoformat(),
                'end_date': period_end.isoformat(),
                'beginning_nav': round(running_nav, 2),
                'capital_calls': round(capital_calls, 2),
                'redemptions': round(redemptions, 2),
                'denominator': round(denominator, 2),
                'noi': round(noi, 2),
                'interest_expense': round(interest_expense, 2),
                'income': round(income, 2),
                'appreciation': round(appreciation_total, 2),
                'total_return': round(total_return, 2),
                'ending_nav': round(ending_nav, 2),
                'twr': twr,
                'property_details': property_details,
            }
        )

        running_nav = ending_nav
        period_start = period_end + timedelta(days=1)

    return {
        'portfolio_id': portfolio_id,
        'analysis_start_date': start_date.isoformat(),
        'analysis_end_date': end_date.isoformat(),
        'quarters': quarters,
    }


def _prepare_property_states(properties: List[Property], apply_ownership: bool):
    states = {}
    for prop in properties:
        valuation = calculate_property_valuation(prop)
        monthly_values = {}
        prev_value = (prop.market_value_start or 0.0) * (prop.ownership_percent if apply_ownership else 1.0)
        exit_cutoff = _month_end(prop.exit_date) if prop.exit_date else None
        for entry in valuation.get('monthly_market_values', []):
            date_str = entry.get('date')
            if not date_str:
                continue
            try:
                entry_date = datetime.fromisoformat(date_str).date()
            except ValueError:
                continue
            if exit_cutoff and entry_date > exit_cutoff:
                break
            value = entry.get('market_value')
            scaled_value = value * (prop.ownership_percent or 1.0) if apply_ownership and value is not None else value
            monthly_values[entry_date] = {**entry, 'market_value': scaled_value}
        states[prop.id] = {
            'property': prop,
            'prev_value': prev_value,
            'monthly_values': monthly_values,
        }
    return states


def _accumulate_property_events(cash_flows: List[CashFlow]):
    capex = defaultdict(lambda: defaultdict(float))
    sales = defaultdict(dict)
    for cf in cash_flows:
        if not cf.property_id or not cf.date:
            continue
        if cf.cash_flow_type == 'property_capex':
            label = _format_quarter_label(cf.date)
            capex[cf.property_id][label] += cf.amount or 0.0
        elif cf.cash_flow_type == 'property_sale':
            sale_quarter_end = _quarter_end(_quarter_start(cf.date))
            sales[cf.property_id][sale_quarter_end] = cf.amount or 0.0
    return capex, sales


def _calculate_appreciation_for_quarter(
    property_states: Dict[int, dict],
    capex_by_property: Dict[int, Dict[str, float]],
    sales_by_property: Dict[int, Dict[date, float]],
    property_flows: Dict[int, dict],
    quarter_end: date,
    quarter_label: str,
    apply_ownership: bool,
    property_map: Dict[int, Property],
    ownership_lookup: Dict[int, List[Tuple[date, float]]],
) -> Tuple[List[dict], float]:
    total_appreciation = 0.0
    details = []

    for prop_id, state in property_states.items():
        monthly_entry = state['monthly_values'].get(quarter_end)
        property_obj = state['property']
        if not monthly_entry or monthly_entry.get('market_value') is None:
            sale_amount = sales_by_property.get(prop_id, {}).get(quarter_end)
            if sale_amount is None:
                continue
            end_value = sale_amount * (
                _ownership_percent(
                    ownership_lookup.get(prop_id, []),
                    quarter_end,
                    default=property_obj.ownership_percent or 1.0
                ) if apply_ownership else 1.0
            )
        else:
            end_value = monthly_entry['market_value']
        begin_value = state.get('prev_value')
        if begin_value is None:
            begin_value = end_value

        capex_total = -(capex_by_property.get(prop_id, {}).get(quarter_label, 0.0) or 0.0)
        if apply_ownership:
            percent = _ownership_percent(
                ownership_lookup.get(prop_id, []),
                quarter_end,
                default=property_map.get(prop_id).ownership_percent if property_map.get(prop_id) else 1.0
            )
            capex_total *= percent
        appreciation = (end_value - begin_value) - capex_total
        state['prev_value'] = end_value

        flows = property_flows.get(prop_id, {})
        noi = flows.get('noi', 0.0)
        income = noi
        total_return = income + appreciation

        property_denominator = begin_value + 0.5 * capex_total - (noi / 3.0)
        property_twr = total_return / property_denominator if property_denominator else None

        total_appreciation += appreciation
        details.append(
            {
                'property_id': prop_id,
                'property_name': property_obj.property_name or property_obj.property_id,
                'begin_value': round(begin_value, 2),
                'end_value': round(end_value, 2),
                'capex': round(capex_total, 2),
                'appreciation': round(appreciation, 2),
                'capital_calls': round(flows.get('capital_calls', 0.0), 2),
                'redemptions': round(flows.get('redemptions', 0.0), 2),
                'noi': round(noi, 2),
                'interest_expense': 0.0,
                'net_income': round(income, 2),
                'total_return': round(total_return, 2),
                'denominator': round(property_denominator, 2),
                'twr': property_twr,
            }
        )

    details.sort(key=lambda item: item['property_name'])
    return details, total_appreciation


def _summarize_property_flows(
    flows: List[CashFlow],
    property_map: Dict[int, Property],
    ownership_lookup: Dict[int, List[Tuple[date, float]]],
    apply_ownership: bool,
):
    summary = defaultdict(lambda: {'capital_calls': 0.0, 'redemptions': 0.0, 'noi': 0.0, 'interest': 0.0})
    for flow in flows:
        if not flow.property_id or not flow.date:
            continue
        flow_type = (flow.cash_flow_type or '').lower()
        if flow_type not in {'capital_call', 'redemption', 'redemption_payment', 'property_noi', 'loan_interest'}:
            continue
        amount = flow.amount or 0.0
        if apply_ownership:
            property_obj = property_map.get(flow.property_id)
            percent = _ownership_percent(
                ownership_lookup.get(flow.property_id, []),
                flow.date,
                default=property_obj.ownership_percent if property_obj else 1.0
            )
            amount *= percent
        bucket = summary[flow.property_id]
        if flow_type == 'capital_call':
            bucket['capital_calls'] += amount
        elif flow_type in {'redemption', 'redemption_payment'}:
            bucket['redemptions'] += abs(amount)
        elif flow_type == 'property_noi':
            bucket['noi'] += amount
        elif flow_type == 'loan_interest':
            bucket['interest'] += abs(amount)
    return summary


def _sum_amounts(
    flows: List[CashFlow],
    types: set,
    property_map: Dict[int, Property],
    ownership_lookup: Dict[int, List[Tuple[date, float]]],
    absolute: bool = False,
    apply_ownership: bool = False,
) -> float:
    total = 0.0
    for flow in flows:
        flow_type = (flow.cash_flow_type or '').lower()
        if flow_type in types:
            amount = flow.amount or 0.0
            if apply_ownership and flow.property_id:
                property_obj = property_map.get(flow.property_id)
                percent = _ownership_percent(
                    ownership_lookup.get(flow.property_id, []),
                    flow.date,
                    default=property_obj.ownership_percent if property_obj else 1.0
                )
                amount *= percent
            total += abs(amount) if absolute else amount
    return total


def _month_end(value: Optional[date]) -> Optional[date]:
    if value is None:
        return None
    last_day = monthrange(value.year, value.month)[1]
    return value.replace(day=last_day)


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


def _quarter_start(target: date) -> date:
    quarter_month = ((target.month - 1) // 3) * 3 + 1
    return target.replace(month=quarter_month, day=1)


def _quarter_end(quarter_start: date) -> date:
    return quarter_start + relativedelta(months=3) - timedelta(days=1)


def _format_quarter_label(target: date) -> str:
    quarter = ((target.month - 1) // 3) + 1
    return f"Q{quarter} {target.year}"
