import pandas as pd
from datetime import date, datetime
from typing import Optional, List, Tuple
from calendar import monthrange
from decimal import Decimal
from portfolio_manager.Loan import Loan  # Adjust import path as needed


class PreferredEquity:
    def __init__(
        self,
        id: str,
        underlying_loan: Loan,
        initial_pe_ownership: float = 1.0,
    ):
        """
        :param id: Unique identifier for this Preferred Equity investment.
        :param underlying_loan: The Loan object that backs this preferred equity investment.
        :param initial_pe_ownership: The initial ownership share of the preferred equity.
        """
        self.id = id
        self.underlying_loan = underlying_loan
        self.pe_ownership_changes: List[Tuple[date, Decimal]] = []

        # Validate initial ownership
        self._validate_ownership(initial_pe_ownership)

        # Initialize the ownership with an event at the start of the loan schedule
        schedule_start = self._get_schedule_start_date()
        if schedule_start is not None:
            self.add_pe_ownership_change(schedule_start, initial_pe_ownership)

    # ---------------------------------------------------------------------
    #                PREFERRED EQUITY OWNERSHIP LOGIC
    # ---------------------------------------------------------------------
    def add_pe_ownership_change(self, change_date: date, new_ownership: float):
        """
        Record a preferred equity ownership change event at the given date.
        """
        change_date = self.get_end_of_month(change_date)  # Align to month-end
        self._validate_ownership(new_ownership)
        self.pe_ownership_changes.append((change_date, Decimal(new_ownership)))
        # Keep changes sorted by date
        self.pe_ownership_changes.sort(key=lambda x: x[0])

    def get_ownership_share(self, query_date: date) -> Decimal:
        """
        Get the preferred equity ownership share for a specific date.
        If no change date is prior, it defaults to 0.0.
        """
        query_date = self.get_end_of_month(query_date)
        if not self.pe_ownership_changes:
            return Decimal(0.0)

        # Find the most recent change before or on query_date
        for change_date, ownership_share in reversed(self.pe_ownership_changes):
            if query_date >= change_date:
                return ownership_share
        return Decimal(0.0)

    def generate_pe_ownership_series(self) -> dict:
        """
        Generate a dictionary of {date: ownership_share} for all dates
        in the underlying loan schedule. Each date will be the last day of
        the month, consistent with the loan schedule.
        """
        # Retrieve all schedule dates from the loan
        df_loan = self.underlying_loan.generate_loan_schedule_df()
        if df_loan.empty:
            return {}

        df_loan['date'] = df_loan['date'].apply(self.get_end_of_month)
        schedule_dates = sorted(df_loan['date'].unique())

        # Build the ownership series
        ownership_series = {}
        current_ownership = Decimal(0.0)
        change_idx = 0

        for d in schedule_dates:
            while change_idx < len(self.pe_ownership_changes) and d >= self.pe_ownership_changes[change_idx][0]:
                _, current_ownership = self.pe_ownership_changes[change_idx]
                change_idx += 1
            ownership_series[d] = current_ownership

        return ownership_series

    def get_end_of_month(self, input_date: date) -> date:
        """
        Ensure the date is a `date` object and align it to the last day of the month.
        """
        if pd.isna(input_date):  # Handle NaN or NaT
            return None

        # Convert to date object if needed
        if isinstance(input_date, pd.Timestamp):
            input_date = input_date.date()
        elif isinstance(input_date, datetime):
            input_date = input_date.date()
        elif not isinstance(input_date, date):
            raise ValueError(f"Invalid date format: {input_date}")

        # Ensure the date is the last day of the month
        last_day = monthrange(input_date.year, input_date.month)[1]
        return input_date.replace(day=last_day)

    # ---------------------------------------------------------------------
    #               GENERATE PREFERRED EQUITY CASH FLOWS
    # ---------------------------------------------------------------------
    def generate_preferred_equity_schedule_df(self) -> pd.DataFrame:
        """
        Generates a DataFrame reflecting cash flows as if the Preferred Equity
        owns 100% of the underlying loan.
        """
        df_loan = self.underlying_loan.generate_loan_schedule_df()
        if df_loan.empty:
            return pd.DataFrame()

        df_loan['date'] = df_loan['date'].apply(self.get_end_of_month)

        # Rename columns for preferred equity perspective
        df_loan['noi'] = df_loan['interest_payment']
        df_loan['preferred_equity_repayment'] = (
            df_loan['scheduled_principal_payment'] + df_loan['loan_paydown']
        )
        df_loan['preferred_equity_draw'] = df_loan['loan_draw']
        df_loan['market_value'] = df_loan['ending_balance']
        df_loan['Property Name'] = f"Preferred Equity: Loan #{self.underlying_loan.id}"
        df_loan['Property Type'] = "Preferred Equity"

        # Keep only relevant columns
        df_loan = df_loan[['date', 'Property Name', 'Property Type', 'noi', 'preferred_equity_draw',
                           'preferred_equity_repayment', 'market_value']].copy()
        df_loan.sort_values('date', inplace=True)
        return df_loan

    def generate_preferred_equity_schedule_share_df(self) -> pd.DataFrame:
        """
        Generates a DataFrame that applies the Preferred Equity ownership
        shares to the 'full ownership' amounts.
        """
        df_full = self.generate_preferred_equity_schedule_df()
        if df_full.empty:
            return pd.DataFrame()

        ownership_dict = self.generate_pe_ownership_series()
        df_ownership = pd.DataFrame(list(ownership_dict.items()), columns=['date', 'ownership_share'])
        df_ownership['date'] = df_ownership['date'].apply(self.get_end_of_month)  # Align dates
        df_ownership['ownership_share'] = df_ownership['ownership_share'].astype(float)
        df_ownership.sort_values('date', inplace=True)

        # Merge and scale amounts by ownership share
        df_merged = pd.merge(df_full, df_ownership, on='date', how='left')
        df_merged['ownership_share'] = df_merged['ownership_share'].fillna(0.0)
        for col in ['noi', 'preferred_equity_draw', 'preferred_equity_repayment', 'market_value']:
            df_merged[col] *= df_merged['ownership_share']

        return df_merged[['date', 'Property Name', 'Property Type', 'ownership_share','noi', 'preferred_equity_draw',
                           'preferred_equity_repayment', 'market_value']].copy()

    def get_preferred_equity_schedule_share_df_by_date(self, start_date, end_date):
        df = self.generate_preferred_equity_schedule_share_df()
        return df.loc[ (df.date >= start_date) & (df.date <= end_date)]
    # ---------------------------------------------------------------------
    #                       HELPER METHODS
    # ---------------------------------------------------------------------
    def _get_schedule_start_date(self) -> Optional[date]:
        """
        Returns the earliest date from the loan’s schedule. If none exists,
        returns None.
        """
        df_schedule = self.underlying_loan.generate_loan_schedule_df()
        if df_schedule.empty:
            return None
        min_ts = df_schedule['date'].min()
        return self.get_end_of_month(min_ts)

    def _validate_ownership(self, ownership: float):
        """
        Ensure the ownership value is between 0.0 and 1.0.
        """
        if not (0.0 <= ownership <= 1.0):
            raise ValueError(f"Ownership must be between 0.0 and 1.0, got {ownership}.")