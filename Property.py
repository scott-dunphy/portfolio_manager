from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from collections import OrderedDict
from typing import Optional
from portfolio_manager.Loan import Loan
import pandas as pd
from itertools import accumulate
import logging

class Property:

    def __init__(self,
                 id: str,
                 name: str,
                 property_type: str,
                 acquisition_date: date,
                 disposition_date: date,
                 acquisition_cost: float,
                 disposition_price: float,
                 building_size: float,
                 address: Optional[str],
                 city: Optional[str],
                 state: Optional[str],
                 zipcode: Optional[int],
                 market_value: float,
                 analysis_date: date,
                 analysis_length: int,
                 loans: Optional[dict],
                 market_value_growth: Optional[float]=.03,
                 ownership: Optional[float]=1,
                 construction_end: Optional[date] = None,
                 equity_commitment: Optional[float] = None,
                 partial_sale_date: Optional[date] = None,
                 partial_sale_proceeds: Optional[float] = 0,
                 partial_sale_percent: Optional[float] = 0,
                 partner_buyout_date: Optional[date] = None,
                 partner_buyout_cost: Optional[float] = 0,
                 partner_buyout_percent: Optional[float] = 0,
                 encumbered: Optional[bool] = False,
                 ):
        self.id = str(id)
        self.name = name
        self.property_type = property_type
        self.address = address
        self.city = city
        self.state = state
        self.zipcode = zipcode
        self.building_size = building_size
        self.acquisition_date = self.get_last_day_of_month(acquisition_date)
        self.disposition_date = self.get_last_day_of_month(disposition_date)
        self.acquisition_cost = acquisition_cost
        self.disposition_price = disposition_price
        self.loans = loans or {}
        self.analysis_date = self.get_last_day_of_month(analysis_date)
        self.analysis_length = int(analysis_length)
        self.market_value = market_value
        self.market_value_growth = market_value_growth
        self.ownership = ownership
        self.noi = {}
        self.capex = {}
        self.month_list = self.get_month_list(self.analysis_date, self.analysis_length)
        self.ownership_changes = []
        self.construction_end = construction_end
        self.equity_commitment = equity_commitment
        self.partial_sale_date = partial_sale_date
        self.partner_buyout_date = partner_buyout_date
        self.partial_sale_proceeds = partial_sale_proceeds
        self.partner_buyout_cost = partner_buyout_cost
        self.partner_buyout_percent = partner_buyout_percent
        self.partial_sale_percent = partial_sale_percent
        self.encumbered = encumbered

        # Ensure initial ownership is set
        if self.acquisition_date and not pd.isna(self.acquisition_date):
            self.add_ownership_change(self.acquisition_date, self.ownership)

        if self.disposition_date and not pd.isna(self.disposition_date):
            next_month = self.disposition_date + relativedelta(months=1)
            last_day_of_next_month = next_month.replace(
                day=monthrange(next_month.year, next_month.month)[1]
            )
            self.add_ownership_change(last_day_of_next_month, 0)

        if self.partial_sale_date and not pd.isna(self.partial_sale_date) and self.partial_sale_percent != 0:
            self.add_partial_sale(self.partial_sale_date, self.partial_sale_proceeds, -self.partial_sale_percent)

        if self.partner_buyout_date and not pd.isna(self.partner_buyout_date) and self.partner_buyout_percent != 0:
            self.add_partner_buyout(self.partner_buyout_date, self.partner_buyout_cost, self.partner_buyout_percent)

        self.add_ownership_change(self.get_last_day_of_month(self.disposition_date + relativedelta(days=1)), 0)
        self.unfunded_equity_commitments = []

    def get_last_day_of_month(self, input_date) -> date:
        if pd.isna(input_date):  # Handle NaN, NaT, or blank cells
            return None
        if not isinstance(input_date, date):  # Ensure input_date is a valid date object
            raise ValueError(f"Invalid date: {input_date}")

        last_day = monthrange(input_date.year, input_date.month)[1]
        return input_date.replace(day=last_day)

    def compare_property_and_loan_dates(self):
        for loan in self.loans.values():
            if min(loan.prepayment_date, loan.maturity_date) > self.disposition_date:
                logging.warning(f"Loan maturity/prepayment date is after the disposition date. -- Property: {self.name} | Loan: {loan.id}")

    def ensure_date(self, input_date):
        """Ensure the input is a datetime.date object and adjust to month-end."""
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

    def add_ownership_change(self, change_date: date, new_ownership: float):
        """Add an ownership change event."""
        change_date = self.ensure_date(change_date)  # Ensure the date is a `datetime.date` object
        self.ownership_changes.append((self.get_last_day_of_month(change_date), new_ownership))
        self.ownership_changes.sort()  # Ensure events are sorted by date

    def get_ownership_share(self, query_date: date) -> float:
        """Get the ownership share for a specific date."""
        # Ensure ownership changes are sorted
        self.ownership_changes.sort()

        # Iterate over ownership changes in reverse to find the most recent one
        for change_date, ownership in reversed(self.ownership_changes):
            if query_date >= change_date:
                return ownership

        # Default to 0 ownership if no changes are before the query date
        return 0.0

    def add_partner_buyout(self, buyout_date, cost, share):
        """Add a partner buyout event by increasing the current ownership share."""
        # Ensure date is properly formatted
        buyout_date = self.ensure_date(buyout_date)

        # Get the current ownership share at the buyout date
        current_ownership = self.get_ownership_share(buyout_date)

        # Calculate the new ownership share
        new_ownership = current_ownership + share

        # Update partner buyout cost and add the ownership change
        self.partner_buyout_cost = cost
        # Compute the ownership_change_date as the month-end following buyout_date
        ownership_change_date = self.ensure_date(buyout_date + relativedelta(months=1))

        # Record the ownership change at ownership_change_date
        self.add_ownership_change(ownership_change_date, new_ownership)

    def add_partial_sale(self, partial_date, proceeds, share):
        """Reduce ownership based on a partial sale."""
        partial_date = self.ensure_date(partial_date)

        # Get the current ownership share
        current_ownership = self.get_ownership_share(partial_date)

        # Calculate new ownership after partial sale
        new_ownership = max(current_ownership + share, 0)  # Prevent negative ownership

        # Update the partial sale proceeds and record ownership change
        self.partial_sale_proceeds = proceeds
        self.add_ownership_change(partial_date, new_ownership)

    def generate_ownership_series(self):
        """Generate a time series of ownership percentages without mutating self.ownership_changes."""
        # Make a sorted copy of the ownership changes so we don't alter the original
        changes = sorted(self.ownership_changes, key=lambda x: x[0])

        ownership_series = {}
        current_ownership = self.ownership
        change_idx = 0

        for month in self.month_list:
            # Apply all ownership changes up to and including this month
            while change_idx < len(changes) and changes[change_idx][0] <= month:
                # Update current ownership based on the event
                _, current_ownership = changes[change_idx]
                change_idx += 1

            # Record the current ownership for this month
            ownership_series[month] = current_ownership

            # Stop updating once we reach or surpass the disposition date
            if self.disposition_date and month >= self.disposition_date:
                break

        return ownership_series

    def get_month_list(self, start_date: date, num_months: int) -> list:
        """Generate a list of the last day of each month, ensuring all are `datetime.date` objects."""
        return [self.ensure_date(self.get_last_day_of_month(start_date + relativedelta(months=i))) for i in
                range(num_months)]

    def get_equity_commitment(self):
        return self.equity_commitment or 0

    def calculate_period_deficit(self, ncf):
        """Calculate the deficit for a period."""
        return max(-ncf, 0)  # Consider deficits only

    def cover_deficit_with_equity(self, deficit, unfunded_equity):
        """Cover as much of the deficit as possible with equity."""
        deficit = max(deficit, 0)
        unfunded_equity = max(unfunded_equity, 0)

        if unfunded_equity >= deficit:
            return 0, unfunded_equity - deficit  # Fully covered by equity
        else:
            return deficit - unfunded_equity, 0  # Remaining deficit after equity exhaustion

    def cover_deficit_with_loans(self, deficit, draw_date, loans):
        """Cover remaining deficit with available loan draws."""
        if not loans:
            return deficit  # No loans available

        for loan_id, loan in loans.items():
            if deficit <= 0:
                break
            draw_amount = self.execute_loan_func(loan_id, Loan.add_loan_draw, deficit, draw_date)
            deficit -= draw_amount

        return deficit  # Return remaining deficit if loans are insufficient

    def calculate_unfunded_equity(self):
        """Calculate the unfunded equity commitments using NOI and CapEx."""
        #if not self.equity_commitment or self.equity_commitment == 0 or pd.isna(self.equity_commitment):
        if pd.isna(self.construction_end) or self.construction_end is None:
            return [0] * len(self.month_list)

        # Initialize variables
        unfunded_equity = self.equity_commitment
        unfunded_equity_commitments = []

        # Iterate through the month list
        for draw_date in self.month_list:
            # Retrieve NOI and CapEx, defaulting to zero if missing
            noi = self.noi.get(draw_date, 0)
            capex = self.capex.get(draw_date, 0)
            period_ncf = noi - capex

            # Step 1: Calculate the period deficit
            deficit = self.calculate_period_deficit(period_ncf)

            # Step 2: Cover deficit with equity
            deficit, unfunded_equity = self.cover_deficit_with_equity(deficit, unfunded_equity)

            # Step 3: Cover remaining deficit with loans
            if deficit > 0:
                deficit = self.cover_deficit_with_loans(deficit, draw_date, self.loans)

            # Step 4: Log error if deficit remains (optional)
            if deficit > 0:
                logging.error(f"{self.name}: Remaining deficit on {draw_date}: {deficit:.2f}")

            # Step 5: Track current unfunded equity balance
            unfunded_equity_commitments.append(unfunded_equity)

        return unfunded_equity_commitments

    def grow_market_value(self):
        growth_rate = (1 + self.market_value_growth) ** (1 / 12)
        market_value = self.market_value
        market_values = []

        # Iterate through months to adjust market value
        for idx, month in enumerate(self.month_list):
            if month < self.disposition_date:
                if idx == 0:
                    # Set the initial market value for the first month
                    current_value = market_value
                else:
                    # Apply CAPEX if within the construction period
                    capex = self.capex.get(month, 0) if self.construction_end and month <= self.construction_end else 0

                    # Update market value with growth and capex
                    current_value = current_value * growth_rate + capex
            elif month == self.disposition_date:
                # Set market value to 0 on the disposition date
                current_value = 0
            else:
                # Ensure market value remains 0 after disposition
                current_value = 0

            market_values.append(current_value)

        return market_values

    def get_disposition_date(self):
        return self.disposition_date

    def get_acquisition_date(self):
        return self.acquisition_date

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def update_market_value(self, market_value):
        self.market_value = market_value
        return

    def update_noi(self, noi: dict):
        self.noi = noi


    def update_capex(self, capex: dict):
        self.capex = capex

    def update_noi_by_date(self, date_, noi):
        date_ = self.ensure_date(date_)
        if date_ is None:
            raise ValueError("The provided date is invalid or could not be converted.")
        if not isinstance(noi, (int, float)):
            raise TypeError(f"Invalid NOI type: {type(noi)}. Expected int or float.")
        if date_ not in self.month_list:
            raise ValueError(f"Date {date_} is outside the analysis period.")
        self.noi[date_] = noi

    def update_capex_by_date(self, date_, capex):
        date_ = self.ensure_date(date_)
        if date_ is None:
            raise ValueError("The provided date is invalid or could not be converted.")
        if not isinstance(capex, (int, float)):
            raise TypeError(f"Invalid NOI type: {type(capex)}. Expected int or float.")
        if date_ not in self.month_list:
            raise ValueError(f"Date {date_} is outside the analysis period.")
        self.capex[date_] = capex

    def get_capex(self, date_,):
        date_ = self.ensure_date(date_)
        return self.capex[date_]

    def get_noi(self, date_,):
        date_ = self.ensure_date(date_)
        return self.noi[date_]

    def get_cash_flows_df(self):
        # Create the base DataFrame with dates and market value growth
        df = pd.DataFrame(
            list(zip(self.month_list, self.grow_market_value())),
            columns=['date', 'market_value']
        )

        # Populate key financial events
        df.loc[df.date == self.acquisition_date, 'acquisition_cost'] = self.acquisition_cost
        df.loc[df.date == self.disposition_date, 'disposition_price'] = self.disposition_price
        df.loc[df.date == self.partner_buyout_date, 'partner_buyout_cost'] = self.partner_buyout_cost
        df.loc[df.date == self.partial_sale_date, 'partial_sale_proceeds'] = self.partial_sale_proceeds

        # Populate cash flows from the stored dictionaries
        df['noi'] = df['date'].map(self.noi).fillna(0)
        df['capex'] = df['date'].map(self.capex).fillna(0)

        return df

    def add_loan(self, loan: Loan):
        if not isinstance(self.loans, dict):
            print(f"Unexpected type for self.loans: {type(self.loans)}. Reinitializing.")
            self.loans = {}

        loan_id = str(loan.id)
        if loan_id in self.loans:
            raise ValueError(f"Loan with ID {loan_id} already exists.")

        self.loans[loan_id] = loan
        maturity_date = loan.maturity_date
        prepayment_date = loan.prepayment_date
        fallback_date = date.max
        earliest_date = min(maturity_date or fallback_date, prepayment_date or fallback_date)
        if earliest_date > self.disposition_date:
            logging.warning(f"Loan maturity/prepayment date is after the disposition date. -- Property: {self.name} | Loan: {loan.id}")

    def remove_loan(self, id):
        if id in self.loans:
            del self.loans[id]

    def get_loan(self, id):
        if id in self.loans:
            return self.loans.get(id)

    def update_loan(self, id, **kwargs):
        if id in self.loans:
            loan = self.loans.get(id)
            for k,v in kwargs.items():
                setattr(loan, k, v)

    def execute_loan_func(self, loan_id, func, *args, **kwargs):
        loan_id = str(loan_id)  # Ensure loan_id is a string
        loan = self.get_loan(loan_id)
        if not loan:
            raise KeyError(f"Loan ID {loan_id} not found.")

        # Execute the function on the loan
        return func(loan, *args, **kwargs)

    def add_loan_draw(self, loan_id: str, draw: float, draw_date: date):
        draw = self.execute_loan_func(loan_id, Loan.add_loan_draw, draw=draw, draw_date=draw_date)
        return draw

    def add_loan_paydown(self, loan_id: str, paydown: float, paydown_date: date):
        self.execute_loan_func(loan_id, Loan.add_loan_paydown, paydown=paydown, draw_date=paydown_date)
        return

    def generate_loan_schedule_df(self, loan_id: str):
        self.execute_loan_func(loan_id, Loan.generate_loan_schedule_df)
        return

    def check_loan_dates(self):
        for loan in self.loans.values():
            # Replace None with a fallback date for comparison
            maturity_date = loan.maturity_date or date.max
            prepayment_date = loan.prepayment_date or date.max
            foreclosure_date = loan.foreclosure_date or date.max

            # Find the earliest of the available dates
            min_date = min(maturity_date, prepayment_date, foreclosure_date)

            if min_date > self.disposition_date:
                logging.warning(
                    f"Loan dates extend beyond disposition. Property: {self.name}, Loan: {loan.id}"
                )
    def combine_loan_schedules_df(self):
        if len(self.loans) == 0:
            return None
        else:
            self.check_loan_dates()
            loans_ = [loan.generate_loan_schedule_df() for loan in self.loans.values()]
            df = pd.concat(loans_)
            df = df.groupby('date').sum().reset_index()
            df['encumbered'] = df['encumbered'] > 0
            #print(df)
            return df

    def combine_loan_cash_flows_df(self):
        if len(self.loans) == 0:
            cash_flows = self.get_cash_flows_df()
            cash_flows['date'] = pd.to_datetime(cash_flows['date'])
            cash_flows['encumbered'] = False
        else:
            cash_flows = self.get_cash_flows_df()
            cash_flows['date'] = pd.to_datetime(cash_flows['date'])
            loan_cash_flows = self.combine_loan_schedules_df()
            loan_cash_flows['date'] = pd.to_datetime(loan_cash_flows['date'])
            cash_flows = cash_flows.merge(loan_cash_flows, on='date',how='left')
            cash_flows['encumbered'] = cash_flows['encumbered']==True
        cash_flows.fillna(0, inplace=True)
        cash_flows['Property Name'] = self.name
        cash_flows['Property Type'] = self.property_type
        if self.encumbered == True:
            cash_flows['encumbered'] = True
        return cash_flows

    def adjust_cash_flows_by_ownership_df(self):
        """Adjust all numeric cash flow columns by the ownership share."""
        cash_flows = self.combine_loan_cash_flows_df()

        # Generate the ownership time series
        ownership_series = pd.DataFrame(
            list(self.generate_ownership_series().items()),
            columns=['date', 'ownership_share']
        )

        # Ensure dates are `date` objects
        cash_flows['date'] = cash_flows['date'].dt.date
        ownership_series['date'] = ownership_series['date'].dt.date

        # Merge ownership series with cash flows
        adjusted_cash_flows = cash_flows.merge(ownership_series, on='date', how='left')

        # Fill missing ownership shares with zero
        adjusted_cash_flows['ownership_share'] = adjusted_cash_flows['ownership_share'].fillna(0)

        # Avoid multiplying specific columns
        exclude_columns = {'partner_buyout_cost',
                           'partial_sale_proceeds',
                           'ownership_share',
                           }

        numeric_columns = adjusted_cash_flows.select_dtypes(include='number').columns

        for col in numeric_columns:
            if col not in exclude_columns:
                adjusted_cash_flows[col] *= adjusted_cash_flows['ownership_share']

        # Adjust the market_value on buyout or partial sale dates
        for event_date, column in [(self.partner_buyout_date, 'partner_buyout_cost'),
                                   (self.partial_sale_date, 'partial_sale_proceeds')]:
            if event_date:
                event_date = self.ensure_date(event_date)
                next_month = self.get_last_day_of_month(event_date + relativedelta(months=1))

                if event_date in adjusted_cash_flows['date'].values and next_month in adjusted_cash_flows[
                    'date'].values:
                    ownership_share_event = adjusted_cash_flows.loc[
                        adjusted_cash_flows['date'] == event_date, 'ownership_share'
                    ].iloc[0]
                    ownership_share_next = adjusted_cash_flows.loc[
                        adjusted_cash_flows['date'] == next_month, 'ownership_share'
                    ].iloc[0]

                    market_value_event = adjusted_cash_flows.loc[
                        adjusted_cash_flows['date'] == event_date, 'market_value'
                    ].iloc[0]

                    corrected_market_value = (
                        market_value_event / ownership_share_event * ownership_share_next
                        if ownership_share_event != 0 else 0
                    )

                    adjusted_cash_flows.loc[
                        adjusted_cash_flows['date'] == event_date, 'market_value'
                    ] = corrected_market_value

        return adjusted_cash_flows

    def get_unencumbered_noi(self, beg_date: date, end_date: date):
        # Combine loan and property cash flows
        df = self.combine_loan_cash_flows_df()

        # Filter DataFrame by date range
        df = df[(df['date'] >= beg_date) & (df['date'] <= end_date)]

        # Calculate unencumbered NOI
        unencumbered_noi = df.loc[df['encumbered'] == False, 'noi'].sum()

        return unencumbered_noi


