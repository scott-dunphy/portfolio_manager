from datetime import date
from types import SimpleNamespace

import pytest

from dateutil.relativedelta import relativedelta

from services.property_valuation_service import (
    _calculate_forward_noi,
    _project_monthly_noi,
    calculate_property_valuation,
)


class DummyManualEntry:
    def __init__(self, year, month=None, annual_noi=None, annual_capex=None):
        self.year = year
        self.month = month
        self.annual_noi = annual_noi
        self.annual_capex = annual_capex


class DummyProperty(SimpleNamespace):
    pass


def _month_end(value: date) -> date:
    """Convenience helper to advance to month end."""
    return (value.replace(day=1) + relativedelta(months=1, days=-1))


def test_project_monthly_noi_uses_manual_entries_before_projection():
    """
    When manual NOI overrides exist, _project_monthly_noi should prefer the monthly override,
    then fall back to annual override before defaulting to the growth model.
    """
    manual_entries = [
        DummyManualEntry(year=2024, month=1, annual_noi=15000),  # monthly override
        DummyManualEntry(year=2024, annual_noi=120000),  # annual override (10k/month)
    ]
    prop = DummyProperty(
        initial_noi=240000,  # would be 20k/month without overrides
        noi_growth_rate=0.05,
        purchase_date=date(2024, 1, 10),
        exit_date=None,
        manual_cash_flows=manual_entries,
        use_manual_noi_capex=True,
        portfolio=SimpleNamespace(analysis_start_date=date(2024, 1, 1)),
    )

    start = _month_end(date(2024, 1, 1))
    end = _month_end(date(2025, 1, 1))
    monthly = _project_monthly_noi(prop, start, end)

    assert monthly[start] == 15000  # explicit monthly override
    feb = _month_end(date(2024, 2, 1))
    assert monthly[feb] == 10000  # from annual override (120000 / 12)
    jan_2025 = _month_end(date(2025, 1, 1))
    assert monthly[jan_2025] == 20000  # falls back to projected NOI (240000 / 12)


def test_calculate_forward_noi_skips_pre_purchase_and_sums_next_year():
    start = _month_end(date(2024, 1, 1))
    months = [_month_end(start + relativedelta(months=i)) for i in range(15)]
    monthly_noi = {month: 1000 + idx * 10 for idx, month in enumerate(months)}

    purchase_month = _month_end(date(2024, 2, 1))
    totals = _calculate_forward_noi(months, monthly_noi, purchase_month=purchase_month)

    assert totals[start] == 0  # month before purchase should be zeroed
    feb_index = months.index(purchase_month)
    expected = sum(monthly_noi[months[i]] for i in range(feb_index + 1, feb_index + 13))
    assert totals[purchase_month] == expected


def test_cap_rate_starts_with_implied_purchase_price_and_interpolates_to_exit():
    portfolio = DummyProperty(
        analysis_start_date=date(2024, 1, 1),
        analysis_end_date=date(2024, 12, 31),
    )
    prop = DummyProperty(
        portfolio=portfolio,
        purchase_price=10000.0,
        market_value_start=20000.0,  # should NOT be used for implied cap
        purchase_date=date(2024, 1, 15),
        exit_date=date(2025, 1, 15),
        exit_cap_rate=0.15,
        initial_noi=1200.0,  # annual
        noi_growth_rate=0.0,
        manual_cash_flows=[],
        use_manual_noi_capex=False,
        disposition_price_override=None,
    )

    valuation = calculate_property_valuation(prop)
    first_cap = valuation["year1_cap_rate"]
    assert first_cap == pytest.approx(0.12)  # 1200 / 10000

    monthly = valuation["monthly_market_values"]
    assert monthly[0]["cap_rate"] == pytest.approx(0.12)
    # Final month (Dec 2024) should be close to the exit cap via interpolation
    assert monthly[-1]["cap_rate"] == pytest.approx(0.1475, rel=1e-3)
