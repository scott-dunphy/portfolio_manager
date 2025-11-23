from datetime import date

from services.covenant_service import _calculate_fund_metrics


def test_calculate_fund_metrics_includes_unencumbered_details():
    month = date(2024, 1, 31)
    property_metrics = {
        month: {
            1: {
                'ttm_noi': 100.0,
                'ttm_debt_service': 0.0,
                'outstanding_debt': 0.0,
                'market_value': 1000.0,
            },
            2: {
                'ttm_noi': 50.0,
                'ttm_debt_service': 25.0,
                'outstanding_debt': 500.0,
                'market_value': 900.0,
            },
        }
    }
    unassigned_metrics = {
        month: {
            'ttm_debt_service': 20.0,
            'outstanding': 200.0,
        }
    }

    results = _calculate_fund_metrics([month], property_metrics, unassigned_metrics)
    fund = results[month]

    assert fund['ttm_noi'] == 150.0
    assert fund['ttm_debt_service'] == 45.0  # property (25) + unsecured (20)
    assert fund['outstanding_debt'] == 700.0  # property (500) + unsecured (200)
    assert fund['market_value'] == 1900.0

    assert fund['unencumbered_ttm_noi'] == 100.0  # only property 1 qualifies
    assert fund['unencumbered_market_value'] == 1000.0
    assert fund['unencumbered_ttm_debt_service'] == 20.0
    assert fund['unencumbered_debt'] == 200.0
    # dscr = NOI / unsecured debt service
    assert fund['unencumbered_dscr'] == 5.0
    # ltv = unsecured debt / unencumbered value
    assert fund['unencumbered_ltv'] == 0.2
