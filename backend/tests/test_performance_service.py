from datetime import date
from types import SimpleNamespace

import pytest

import services.performance_service as performance_service
from services.performance_service import (
    _accumulate_property_events,
    _calculate_appreciation_for_quarter,
    _format_quarter_label,
    _prepare_property_states,
    _quarter_end,
    _summarize_property_flows,
)


def _make_cash_flow(flow_date, flow_type, amount, property_id):
    return SimpleNamespace(
        property_id=property_id,
        date=flow_date,
        cash_flow_type=flow_type,
        amount=amount,
    )


def test_appreciation_is_net_of_capex(monkeypatch):
    quarter_start = date(2024, 1, 1)
    quarter_end = _quarter_end(quarter_start)
    label = _format_quarter_label(quarter_start)

    prop = SimpleNamespace(
        id=1,
        property_name='Alpha',
        ownership_percent=1.0,
        market_value_start=1000.0,
        exit_date=None,
        portfolio=None,
        ownership_events=[],
    )

    monkeypatch.setattr(
        performance_service,
        'calculate_property_valuation',
        lambda _: {
            'monthly_market_values': [
                {'date': quarter_end.isoformat(), 'market_value': 1100.0},
            ]
        },
    )

    states = _prepare_property_states([prop], apply_ownership=False)
    flows = [_make_cash_flow(date(2024, 2, 15), 'property_capex', -100.0, prop.id)]
    capex_by_property, sales_by_property = _accumulate_property_events(flows)
    property_flows = _summarize_property_flows(flows, {prop.id: prop}, {}, False)

    details, appreciation_total = _calculate_appreciation_for_quarter(
        states,
        capex_by_property,
        sales_by_property,
        property_flows,
        quarter_end,
        label,
        False,
        {prop.id: prop},
        {},
    )

    detail = details[0]
    assert appreciation_total == 0.0
    assert detail['begin_value'] == 1000.0
    assert detail['end_value'] == 1100.0
    assert detail['capex'] == 100.0
    assert detail['appreciation'] == 0.0


def test_acquisition_counts_as_capex(monkeypatch):
    quarter_start = date(2024, 1, 1)
    quarter_end = _quarter_end(quarter_start)
    label = _format_quarter_label(quarter_start)

    prop = SimpleNamespace(
        id=10,
        property_name='Delta',
        ownership_percent=1.0,
        market_value_start=0.0,
        exit_date=None,
        portfolio=None,
        ownership_events=[],
    )

    monkeypatch.setattr(
        performance_service,
        'calculate_property_valuation',
        lambda _: {
            'monthly_market_values': [
                {'date': quarter_end.isoformat(), 'market_value': 1200.0},
            ]
        },
    )

    acquisition_flow = _make_cash_flow(quarter_start, 'property_acquisition', -1000.0, prop.id)
    states = _prepare_property_states([prop], apply_ownership=False)
    capex_by_property, sales_by_property = _accumulate_property_events([acquisition_flow])
    property_flows = _summarize_property_flows([acquisition_flow], {prop.id: prop}, {}, False)

    details, appreciation_total = _calculate_appreciation_for_quarter(
        states,
        capex_by_property,
        sales_by_property,
        property_flows,
        quarter_end,
        label,
        False,
        {prop.id: prop},
        {},
    )

    detail = details[0]
    assert detail['capex'] == 1000.0
    assert detail['appreciation'] == 200.0  # 1200 end value - 0 starting value - 1000 capex
    assert appreciation_total == 200.0


def test_sale_valuation_uses_sale_amount_when_missing_market_value(monkeypatch):
    quarter_start = date(2024, 4, 1)
    quarter_end = _quarter_end(quarter_start)
    label = _format_quarter_label(quarter_start)

    prop = SimpleNamespace(
        id=2,
        property_name='Beta',
        ownership_percent=0.5,
        market_value_start=800.0,
        exit_date=None,
        portfolio=None,
        ownership_events=[],
    )

    monkeypatch.setattr(
        performance_service,
        'calculate_property_valuation',
        lambda _: {'monthly_market_values': []},
    )

    states = _prepare_property_states([prop], apply_ownership=True)
    flows = [_make_cash_flow(date(2024, 5, 10), 'property_sale', 1000.0, prop.id)]
    capex_by_property, sales_by_property = _accumulate_property_events(flows)
    property_flows = _summarize_property_flows(flows, {prop.id: prop}, {}, True)

    details, appreciation_total = _calculate_appreciation_for_quarter(
        states,
        capex_by_property,
        sales_by_property,
        property_flows,
        quarter_end,
        label,
        True,
        {prop.id: prop},
        {},
    )

    detail = details[0]
    assert detail['begin_value'] == 400.0  # ownership-applied opening balance
    assert detail['end_value'] == 500.0  # ownership-applied sale proceeds
    assert detail['appreciation'] == 100.0
    assert appreciation_total == 100.0
    assert detail['twr'] == 0.25


def test_property_twr_blends_appreciation_noi_and_capex(monkeypatch):
    quarter_start = date(2024, 7, 1)
    quarter_end = _quarter_end(quarter_start)
    label = _format_quarter_label(quarter_start)

    prop = SimpleNamespace(
        id=3,
        property_name='Gamma',
        ownership_percent=1.0,
        market_value_start=1000.0,
        exit_date=None,
        portfolio=None,
        ownership_events=[],
    )

    monkeypatch.setattr(
        performance_service,
        'calculate_property_valuation',
        lambda _: {
            'monthly_market_values': [
                {'date': quarter_end.isoformat(), 'market_value': 1150.0},
            ]
        },
    )

    flows = [
        _make_cash_flow(date(2024, 8, 15), 'property_capex', -100.0, prop.id),
        _make_cash_flow(date(2024, 9, 1), 'property_noi', 90.0, prop.id),
    ]

    states = _prepare_property_states([prop], apply_ownership=False)
    capex_by_property, sales_by_property = _accumulate_property_events(flows)
    property_flows = _summarize_property_flows(flows, {prop.id: prop}, {}, False)

    details, appreciation_total = _calculate_appreciation_for_quarter(
        states,
        capex_by_property,
        sales_by_property,
        property_flows,
        quarter_end,
        label,
        False,
        {prop.id: prop},
        {},
    )

    detail = details[0]
    assert detail['appreciation'] == 50.0
    assert detail['noi'] == 90.0
    assert detail['total_return'] == 140.0
    assert detail['denominator'] == 1020.0
    assert detail['twr'] == pytest.approx(140.0 / 1020.0)
    assert appreciation_total == 50.0
