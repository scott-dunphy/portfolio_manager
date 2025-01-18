import math
from datetime import date
from typing import List, Dict, NamedTuple, Tuple
from scipy.optimize import newton

class TierParams(NamedTuple):
    """Container for each tier's parameters."""
    lp_dist_ratio: float  # e.g. 0.9 = 90% LP
    hurdle_rate: float = 9  # e.g. 0.08 = 8% annual

    @property
    def gp_dist_ratio(self) -> float:
        """Calculate GP distribution ratio as 1 - LP distribution ratio."""
        return 1.0 - self.lp_dist_ratio

class CarriedInterest:
    """
    Flexible carried interest calculator that handles any number of tiers.
    """
    def __init__(
            self,
            deal_dates: List[date],
            deal_cash_flows: List[float],
            tiers: List[TierParams]
    ):
        if len(deal_dates) != len(deal_cash_flows):
            raise ValueError("deal_dates and deal_cash_flows must have the same length.")

        for tier in tiers:
            if not math.isclose(tier.lp_dist_ratio + tier.gp_dist_ratio, 1.0, rel_tol=1e-3):
                raise ValueError(f"Tier distribution ratios must sum to 1.0, but got {tier.lp_dist_ratio} + {tier.gp_dist_ratio}.")

        # Sum cash flows by date before storing them
        self.deal_dates, self.deal_cash_flows = sum_cash_flows_by_date(deal_dates, deal_cash_flows)

        self.tiers = tiers

        self.lp_cash_flows = [0.0] * len(self.deal_cash_flows)
        self.gp_cash_flows = [0.0] * len(self.deal_cash_flows)

    def day_count_fraction(self, d1: date, d0: date) -> float:
        """Year fraction between two dates, assuming 365-day year."""
        return (d1 - d0).days / 365.0

    def xnpv(self, rate: float, cash_flows: List[float], dates: List[date]) -> float:
        """
        Computes the NPV of irregular cash flows.
        """
        if rate <= -1.0:
            return float('inf')

        d0 = dates[0]
        total = 0.0

        for cf, d in zip(cash_flows, dates):
            t = (d - d0).days / 365.0
            total += cf / ((1 + rate) ** t)

        return round(total, 10)

    def xirr(self, cash_flows: List[float], dates: List[date], guess: float = 0.1) -> float:
        if not cash_flows or not dates:
            return 0.0

        def npv(rate):
            return self.xnpv(rate, cash_flows, dates)

        try:
            irr = newton(npv, guess, tol=1e-12)
        except RuntimeError:
            # If Newton-Raphson fails, return a default value
            irr = 0.0
        return round(irr, 10)

    def _initial_allocation(self):
        """
        Allocate negative flows between LP and GP according to the first tier's ratio.
        """
        first_tier = self.tiers[0]
        for i, cf in enumerate(self.deal_cash_flows):
            if cf < 0:
                self.lp_cash_flows[i] = cf * first_tier.lp_dist_ratio
                self.gp_cash_flows[i] = cf * first_tier.gp_dist_ratio
            else:
                self.lp_cash_flows[i] = 0.0
                self.gp_cash_flows[i] = 0.0

    def _future_value(self, up_to_index: int, cf_array: List[float], rate: float) -> float:
        """
        Computes the future value needed to meet the hurdle rate.
        """
        d0 = self.deal_dates[0]
        npv = 0.0
        for j in range(up_to_index + 1):
            t = self.day_count_fraction(self.deal_dates[j], d0)
            npv += cf_array[j] / ((1 + rate) ** t)
        npv = -npv  # Match VBA's multiplication by -1
        t_current = self.day_count_fraction(self.deal_dates[up_to_index], d0)
        fv = npv * ((1 + rate) ** t_current)
        return round(fv, 10)

    def _tier_distribution(self):
        """
        Distributes positive cash flows across tiers sequentially.
        """
        for i in range(len(self.deal_cash_flows)):
            cf = self.deal_cash_flows[i]
            if cf > 0:
                remaining_cf = cf
                for tier in self.tiers:
                    required_fv = self._future_value(i, self.lp_cash_flows, tier.hurdle_rate)
                    alloc_lp = min(required_fv, remaining_cf * tier.lp_dist_ratio)
                    alloc_gp = alloc_lp * (tier.gp_dist_ratio / tier.lp_dist_ratio)
                    self.lp_cash_flows[i] += alloc_lp
                    self.gp_cash_flows[i] += alloc_gp
                    remaining_cf -= (alloc_lp + alloc_gp)
                    if remaining_cf <= 1e-12:
                        break
                # After all tiers, allocate remaining cash to LP and GP based on last tier's ratios
                if remaining_cf > 1e-12:
                    last_tier = self.tiers[-1]
                    self.lp_cash_flows[i] += remaining_cf * last_tier.lp_dist_ratio
                    self.gp_cash_flows[i] += remaining_cf * last_tier.gp_dist_ratio

    def _compute_irr_multiple(self) -> Dict[str, float]:
        """
        Computes IRRs and multiples for the deal, LP, and GP.
        """
        deal_irr = self.xirr(self.deal_cash_flows, self.deal_dates)
        lp_irr = self.xirr(self.lp_cash_flows, self.deal_dates)
        gp_irr = self.xirr(self.gp_cash_flows, self.deal_dates)

        deal_contrib = -sum(cf for cf in self.deal_cash_flows if cf < 0)
        lp_contrib = -sum(cf for cf in self.lp_cash_flows if cf < 0)
        gp_contrib = -sum(cf for cf in self.gp_cash_flows if cf < 0)

        deal_distr = sum(cf for cf in self.deal_cash_flows if cf > 0)
        lp_distr = sum(cf for cf in self.lp_cash_flows if cf > 0)
        gp_distr = sum(cf for cf in self.gp_cash_flows if cf > 0)

        deal_profit = sum(self.deal_cash_flows)
        lp_profit = sum(self.lp_cash_flows)
        gp_profit = sum(self.gp_cash_flows)

        deal_multiple = deal_distr / deal_contrib if deal_contrib != 0 else float('inf')
        lp_multiple = lp_distr / lp_contrib if lp_contrib != 0 else float('inf')
        gp_multiple = gp_distr / gp_contrib if gp_contrib != 0 else float('inf')

        if len(self.deal_cash_flows) == 1:
            lp_effective_share = self.tiers[0].lp_dist_ratio
            gp_effective_share = 1 - lp_effective_share
        elif deal_distr > 0:
            lp_effective_share = lp_distr / deal_distr
            gp_effective_share = gp_distr / deal_distr
        else:
            lp_effective_share = self.tiers[0].lp_dist_ratio
            gp_effective_share = 1 - lp_effective_share
        # Debug prints can be commented out if not needed
        # print(self.deal_cash_flows)
        # print(self.deal_dates)

        assert math.isclose(lp_effective_share + gp_effective_share, 1, rel_tol=1e-5), \
            f"Shares do not sum to 1. LP: {lp_effective_share}, GP: {gp_effective_share}"

        self.lp_effective_share = lp_effective_share

        return {
            "Deal Profit": deal_profit,
            "LP Profit": lp_profit,
            "GP Profit": gp_profit,
            "Deal XIRR": deal_irr,
            "LP XIRR": lp_irr,
            "GP XIRR": gp_irr,
            "Deal Contrib": deal_contrib,
            "LP Contrib": lp_contrib,
            "GP Contrib": gp_contrib,
            "Deal Distr": deal_distr,
            "LP Distr": lp_distr,
            "GP Distr": gp_distr,
            "Deal Multiple": deal_multiple,
            "LP Multiple": lp_multiple,
            "GP Multiple": gp_multiple,
            "LP Effective Share": lp_effective_share,
            "GP Effective Share": gp_effective_share,
        }

    def get_lp_effective_share(self):
        self.calculate()
        return self.lp_effective_share

    def calculate(self) -> Dict[str, float]:
        if not self.deal_dates or not self.deal_cash_flows:
            self.lp_effective_share = self.tiers[0].lp_dist_ratio if self.tiers else 0.0
            return {
                "LP Effective Share": self.lp_effective_share,
            }
        self._initial_allocation()
        self._tier_distribution()
        return self._compute_irr_multiple()


def sum_cash_flows_by_date(dates: List[date], cash_flows: List[float]) -> Tuple[List[date], List[float]]:
    """
    Sum cash flows that occur on the same date.
    Filters out any entries where the date is None or the cash flow is NaN.
    Returns new lists of dates and summed cash flows where each date is unique.
    """
    summed = {}
    for d, cf in zip(dates, cash_flows):
        # Skip entries where the date is None or the cash flow is NaN
        if d is None or cf is None or math.isnan(cf):
            continue

        if d in summed:
            summed[d] += cf
        else:
            summed[d] = cf

    # Sort the dates to maintain chronological order
    sorted_dates = sorted(summed.keys())
    summed_cash_flows = [summed[d] for d in sorted_dates]
    return sorted_dates, summed_cash_flows

