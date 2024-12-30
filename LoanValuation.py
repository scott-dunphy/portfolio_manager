from datetime import timedelta, date
from typing import Optional
import pandas as pd
import requests


class LoanValuation:
    def __init__(self, funding_date: date, note_rate: float, fred_api_key: str):
        self.funding_date = funding_date  # Funding date of the loan
        self.note_rate = note_rate  # Loan's note rate at origination
        self.fred_api_key = fred_api_key  # Your FRED API key
        self.treasury_rates = {}  # Cache for storing fetched Treasury rates
        self.fetch_treasury_rates(start_date=date(2013, 1, 1), end_date=date(2099, 12, 31))

    def fetch_treasury_rates(self, start_date: date, end_date: date, series_id: str = 'DGS10'):
        """
        Fetch Treasury rates for a range of dates from the FRED API and cache them.
        Parameters:
        - start_date: The earliest date to fetch rates for.
        - end_date: The latest date to fetch rates for.
        - series_id: FRED series ID (default: 'DGS10' for 10-Year Treasury Rate).
        """
        base_url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.fred_api_key,
            "file_type": "json",
            "observation_start": start_date.strftime("%Y-%m-%d"),
            "observation_end": end_date.strftime("%Y-%m-%d"),
        }

        response = requests.get(base_url, params=params)
        #print(response.json())

        if response.status_code == 200:
            data = response.json()
            observations = data.get("observations", [])
            for obs in observations:
                obs_date = date.fromisoformat(obs["date"])
                try:
                    self.treasury_rates[obs_date] = float(obs["value"]) / 100  # Convert percentage to decimal
                except ValueError:
                    continue  # Skip invalid data
        else:
            raise ValueError(f"FRED API request failed: {response.status_code}, {response.text}")

    def get_treasury_rate(self, target_date: date) -> float:
        """
        Get the Treasury rate for the nearest available date using cached rates.
        Parameters:
        - target_date: Date to fetch the Treasury rate for.
        Returns:
        - float: The Treasury rate as a decimal (e.g., 0.02 for 2%).
        """
        # Check if the exact date is cached
        if target_date in self.treasury_rates:
            return self.treasury_rates[target_date]

        # If not cached, find the nearest available date before target_date
        available_dates = sorted(d for d in self.treasury_rates if d <= target_date)
        if available_dates:
            return self.treasury_rates[available_dates[-1]]

        raise ValueError(f"No Treasury rate available for or before {target_date}")

    def calculate_spread_at_origination(self) -> float:
        """
        Calculate the spread over the Treasury rate at origination.
        """
        treasury_rate_date = self.funding_date - timedelta(days=60)  # 2 months before funding
        treasury_rate_at_funding = self.get_treasury_rate(treasury_rate_date)
        spread = self.note_rate - treasury_rate_at_funding
        self.spread = spread
        return spread

    def calculate_discount_rate(self, as_of_date: date, spread_at_origination: float) -> float:
        """
        Calculate the discount rate for valuing the loan.
        """
        current_treasury_rate = self.get_treasury_rate(as_of_date)
        discount_rate = spread_at_origination + current_treasury_rate
        self.discount_rate = discount_rate
        return discount_rate

    def filter_schedule_after_as_of_date(self, schedule_df: pd.DataFrame, as_of_date: date) -> pd.DataFrame:
        """
        Filter the loan schedule to include only cash flows after the as_of_date.
        """
        return schedule_df[schedule_df['date'] > as_of_date]

    def calculate_present_value(self, schedule_df: pd.DataFrame, discount_rate: float, as_of_date: date) -> float:
        """
        Calculate the present value of the loan based on future cash flows.
        """
        market_value = 0.0
        for _, row in schedule_df.iterrows():
            cash_flow_date = row['date']
            cash_flow = (
                row['interest_payment']
                + row['scheduled_principal_payment']
                + row['loan_paydown']
                - row['loan_draw']
            )
            months_elapsed = (cash_flow_date.year - as_of_date.year) * 12 + (cash_flow_date.month - as_of_date.month)
            discounted_cash_flow = cash_flow / ((1 + discount_rate / 12) ** months_elapsed)
            market_value += discounted_cash_flow
        return market_value

    def calculate_loan_market_value(self, as_of_date: date, schedule_df: pd.DataFrame) -> float:
        """
        Main function to calculate the market value of the loan.
        """
        # Step 1: Fetch Treasury rates for efficiency
        funding_treasury_date = self.funding_date - timedelta(days=60)
        self.fetch_treasury_rates(start_date=funding_treasury_date, end_date=as_of_date)

        # Step 2: Calculate spread at origination
        spread_at_origination = self.calculate_spread_at_origination()

        # Step 3: Calculate discount rate
        discount_rate = self.calculate_discount_rate(as_of_date, spread_at_origination)

        # Step 4: Filter loan schedule
        filtered_schedule = self.filter_schedule_after_as_of_date(schedule_df, as_of_date)

        # Step 5: Calculate present value
        return self.calculate_present_value(filtered_schedule, discount_rate, as_of_date)


# Example Usage
loan_schedule = pd.DataFrame({
    'date': [date(2024, 4, 1), date(2024, 5, 1), date(2024, 6, 1)],
    'interest_payment': [1000, 1000, 1000],
    'scheduled_principal_payment': [200, 200, 200],
    'loan_draw': [0, 0, 0],
    'loan_paydown': [0, 0, 0]
})

loan = LoanValuation(funding_date=date(2017, 1, 1), note_rate=0.05, fred_api_key="b73eb39061969ce96b4a673f93d0898e")

market_value = loan.calculate_loan_market_value(as_of_date=date(2024, 4, 1), schedule_df=loan_schedule)
print(f"Loan Market Value: {market_value:.2f}")
print(f"Loan Spread: {loan.spread:.5f}")