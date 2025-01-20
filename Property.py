from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from collections import OrderedDict
from typing import Optional
from portfolio_manager.Loan import Loan
from portfolio_manager.CarriedInterest import CarriedInterest, TierParams
import pandas as pd
from itertools import accumulate
import logging
import numpy_financial as npf

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
                 upper_tier_share: Optional[float] = None,
                 construction_end: Optional[date] = None,
                 equity_commitment: Optional[float] = None,
                 partial_sale_date: Optional[date] = None,
                 partial_sale_proceeds: Optional[float] = 0,
                 partial_sale_percent: Optional[float] = 0,
                 partner_buyout_date: Optional[date] = None,
                 partner_buyout_cost: Optional[float] = 0,
                 partner_buyout_percent: Optional[float] = 0,
                 encumbered: Optional[bool] = False,
                 cap_rate: Optional[float] = None,
                 capex_percent_of_noi: Optional[float] = 0,
                 promote = False,
                 exit_cap_rate: Optional[float] = None,


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
        self.cap_rate = cap_rate
        self.exit_cap_rate = exit_cap_rate
        self.capex_percent_of_noi = capex_percent_of_noi
        self.disposition_price = disposition_price
        self.loans = loans or {}
        self.analysis_date = self.ensure_date(self.get_last_day_of_month(analysis_date))
        self.analysis_length = int(analysis_length)
        self.market_value = market_value
        self.market_value_growth = market_value_growth
        self.ownership = ownership
        self.upper_tier_share = upper_tier_share
        self.noi = {}
        self.capex = {}
        self.promote = promote
        self.promote_cash_flows = None
        self.tiers = []
        self.effective_shares = None
        self.month_list = self.get_month_list(self.analysis_date, self.analysis_length)
        self.ownership_changes = []
        self.construction_end = self.ensure_date(construction_end)
        self.equity_commitment = equity_commitment
        self.partial_sale_date = partial_sale_date
        self.partner_buyout_date = partner_buyout_date
        self.partial_sale_proceeds = partial_sale_proceeds
        self.partner_buyout_cost = partner_buyout_cost
        self.partner_buyout_percent = partner_buyout_percent
        self.partial_sale_percent = partial_sale_percent
        self.encumbered = encumbered
        self.treasury_rates = {}
        self.foreclosure_date = None
        self.valuation_method = "cap_rate"

        # Ensure initial ownership is set
        if self.acquisition_date and not pd.isna(self.acquisition_date):
            self.add_ownership_change(self.acquisition_date, self.ownership)

        if self.disposition_date and not pd.isna(self.disposition_date):
            next_month = self.disposition_date + relativedelta(months=1)
            last_day_of_next_month = next_month.replace(day=monthrange(next_month.year, next_month.month)[1])
            self.add_ownership_change(last_day_of_next_month, 0)

        self.process_ownership_events()
        self.unfunded_equity_commitments = []
        self.market_values = self.grow_market_value()

    def get_last_day_of_month(self, input_date) -> date:
        if pd.isna(input_date):  # Handle NaN, NaT, or blank cells
            return None
        if not isinstance(input_date, date):  # Ensure input_date is a valid date object
            raise ValueError(f"Invalid date: {input_date}")

        last_day = monthrange(input_date.year, input_date.month)[1]
        return input_date.replace(day=last_day)

    def add_promote_tier(self, tier: TierParams):
        self.tiers.append(tier)

    def add_promote_cash_flows(self, cash_flow_df: pd.DataFrame):
        # Ensure self.promote_cash_flows is initialized
        if not isinstance(self.promote_cash_flows, pd.DataFrame) or self.promote_cash_flows.empty:
            self.promote_cash_flows = cash_flow_df
        else:
            # Append the new data and reset the index
            self.promote_cash_flows = pd.concat([self.promote_cash_flows, cash_flow_df], ignore_index=True)

        # Convert all dates to `datetime.date` to ensure consistency
        if 'date' in self.promote_cash_flows.columns:
            self.promote_cash_flows['date'] = self.promote_cash_flows['date'].apply(
                lambda x: x.date() if isinstance(x, pd.Timestamp) else x
            )

        # Sort by date for consistency
        self.promote_cash_flows = self.promote_cash_flows.sort_values(by='date').reset_index(drop=True)

    def add_promote_cash_flow(self, date_, cash_flow):
        """
        Adds or updates a single promote cash flow row to the promote_cash_flows DataFrame.

        If a cash flow already exists for the given date, the cash_flow amount will be added to the existing value.
        Otherwise, a new row will be appended.

        Args:
            date_ (date or str): The date of the cash flow.
            cash_flow (float): The cash flow amount.
        """
        # Ensure self.promote_cash_flows is initialized as a DataFrame
        if not isinstance(self.promote_cash_flows, pd.DataFrame):
            self.promote_cash_flows = pd.DataFrame(columns=['date', 'cash_flow'])

        # Normalize the date using ensure_date method
        # This should return a Python date object
        date_ = self.ensure_date(date_)

        # Convert any existing 'date' column entries to date objects if they aren't already
        if not self.promote_cash_flows.empty:
            self.promote_cash_flows['date'] = pd.to_datetime(self.promote_cash_flows['date']).dt.date

        # Check if the date already exists in the DataFrame
        if date_ in self.promote_cash_flows['date'].values:
            # If yes, update the existing cash_flow value by adding the new amount
            mask = self.promote_cash_flows['date'] == date_
            self.promote_cash_flows.loc[mask, 'cash_flow'] += cash_flow
        else:
            # Otherwise, create a new row and append it
            new_row = pd.DataFrame({'date': [date_], 'cash_flow': [cash_flow]})
            self.promote_cash_flows = pd.concat([self.promote_cash_flows, new_row], ignore_index=True)

        # Ensure 'date' column stays as date type and DataFrame is sorted by date
        self.promote_cash_flows['date'] = pd.to_datetime(self.promote_cash_flows['date']).dt.date
        self.promote_cash_flows = self.promote_cash_flows.sort_values(by='date').reset_index(drop=True)


    def get_market_value_by_date(self, date_):
        date_index = self.month_list.index(date_)
        return self.market_values[date_index]

    def get_foreclosure_market_value(self):
        if len(self.loans) > 0:
            for loan in self.loans.values():
                if loan.foreclosure_date:
                    self.foreclosure_date = loan.foreclosure_date
                    date_before_foreclosure = self.ensure_date(loan.foreclosure_date + relativedelta(months=-1))
                    return self.get_market_value_by_date(date_before_foreclosure)
        return 0

    def compare_property_and_loan_dates(self):
        for loan in self.loans.values():
            if min(loan.prepayment_date, loan.maturity_date) > self.disposition_date:
                logging.warning(f"Loan maturity/prepayment date is after the disposition date. -- Property: {self.name} | Loan: {loan.id}")

    def set_treasury_rates(self, treasury_rates):
        self.treasury_rates = treasury_rates

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

    def process_ownership_events(self):
        """Process all ownership changes (buyouts, partial sales, etc.) in chronological order."""
        events = []

        # Initial acquisition ownership
        if self.acquisition_date:
            events.append((self.acquisition_date, self.ownership))

        # Disposition event
        if self.disposition_date:
            effective_date = self.get_last_day_of_month(self.disposition_date + relativedelta(months=1))
            events.append((effective_date, 0.0))

        # Sort all events by date
        events.sort(key=lambda x: x[0])

        # Sequentially process each event, applying buyouts and sales
        current_ownership = self.ownership

        if self.partner_buyout_date and self.partner_buyout_percent != 0:
            # Apply partner buyout to current ownership the month after the buyout date
            effective_date = self.get_last_day_of_month(self.partner_buyout_date)
            new_ownership = min(current_ownership + self.partner_buyout_percent, 1.0)
            events.append((effective_date, new_ownership))
            current_ownership = new_ownership  # Update for subsequent calculations

        if self.partial_sale_date and self.partial_sale_percent != 0:
            # Apply partial sale to current ownership the month after the sale date
            effective_date = self.get_last_day_of_month(self.partial_sale_date + relativedelta(months=1))
            new_ownership = max(current_ownership - self.partial_sale_percent, 0.0)
            events.append((effective_date, new_ownership))
            current_ownership = new_ownership  # Update for subsequent calculations

        # Sort events again in case the partner buyout and partial sale added new dates
        events.sort(key=lambda x: x[0])

        # Reassign the processed events to ownership changes
        self.ownership_changes = [(self.get_last_day_of_month(date), ownership) for date, ownership in events]
    def add_ownership_change(self, change_date: date, new_ownership: float):
        """Add an ownership change event."""
        change_date = self.ensure_date(change_date)  # Ensure the date is a `datetime.date` object
        self.ownership_changes.append((self.get_last_day_of_month(change_date), new_ownership))
        self.ownership_changes.sort()  # Ensure events are sorted by date

    def get_ownership_share(self, query_date: date) -> float:
        """Get the ownership share for a specific date."""
        self.process_ownership_events()  # Ensure events are processed before querying

        if not self.ownership_changes:
            return 0.0  # Default to zero if no changes exist

        for change_date, ownership in reversed(self.ownership_changes):
            if query_date >= change_date:
                return ownership

        return 0.0

    def add_partial_sale(self, partial_date, proceeds, sale_percent):
        """Record a partial sale event."""
        self.partial_sale_date = self.ensure_date(partial_date)
        self.partial_sale_proceeds = proceeds
        self.partial_sale_percent = sale_percent
        self.process_ownership_events()

    def add_partner_buyout(self, buyout_date, cost, buyout_percent):
        """Record a partner buyout event."""
        self.partner_buyout_date = self.ensure_date(buyout_date)
        self.partner_buyout_cost = cost
        self.partner_buyout_percent = buyout_percent
        self.process_ownership_events()

    def generate_ownership_series(self):
        """Generate a time series of ownership percentages without mutating self.ownership_changes."""
        self.process_ownership_events()  # Ensure events are processed before generating the series

        ownership_series = {}
        current_ownership = 0.0  # Default ownership before acquisition
        changes = sorted(self.ownership_changes, key=lambda x: x[0])

        for month in self.month_list:
            # Skip months before acquisition
            if self.acquisition_date and month < self.acquisition_date:
                continue

            # Apply ownership changes
            while changes and changes[0][0] <= month:
                current_ownership = changes.pop(0)[1]

            ownership_series[month] = current_ownership

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
            return deficit, 0, unfunded_equity - deficit  # Fully covered by equity
        else:
            return unfunded_equity, deficit - unfunded_equity, 0  # Remaining deficit after equity exhaustion

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
            equity_contribution, deficit, unfunded_equity = self.cover_deficit_with_equity(deficit, unfunded_equity)
            self.add_promote_cash_flow(draw_date, -equity_contribution)
            # Step 3: Cover remaining deficit with loans
            if deficit > 0:

                deficit = self.cover_deficit_with_loans(deficit, draw_date, self.loans)

            # Step 4: Log error if deficit remains (optional)
            if deficit > 0:
                logging.error(f"{self.name}: Remaining deficit on {draw_date}: {deficit:.2f}")
                self.add_promote_cash_flow(draw_date, -deficit)
            # Step 5: Track current unfunded equity balance
            unfunded_equity_commitments.append(unfunded_equity)

        return unfunded_equity_commitments

    def set_valuation_method(self, valuation_method="cap_rate"):
        self.valuation_method = valuation_method
        return

    def grow_market_value(self):
        growth_rate = (1 + self.market_value_growth) ** (1 / 12)
        market_value = self.market_value
        market_values = []

        # Check if construction has ended or is not defined
        construction_finished = (self.construction_end is None) or (self.construction_end < self.analysis_date)

        # Calculate total months for linear interpolation
        total_months = 120

        # Iterate through months to adjust market value
        for idx, month in enumerate(self.month_list):
            if idx == 0:
                # Initialize current value for the first month
                current_value = market_value
            else:
                # If construction is finished and using cap rate method
                if self.valuation_method == "cap_rate" and construction_finished:
                    months_elapsed = idx
                    fraction = min(months_elapsed / total_months, 1)
                    interpolated_cap_rate = self.cap_rate + fraction * (self.exit_cap_rate - self.cap_rate)
                    current_value = self.capitalize_forward_noi(
                        month, interpolated_cap_rate) if interpolated_cap_rate else 0
                else:
                    # Use growth rate method with CAPEX
                    if month < self.disposition_date:
                        capex = self.capex.get(month,
                                               0) if self.construction_end and month <= self.construction_end else 0
                        current_value = current_value * growth_rate + capex
                    elif month == self.disposition_date:
                        current_value = 0
                    else:
                        current_value = 0

            # Append the current market value to the list
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
        df['foreclosure_market_value'] = 0
        foreclosure_market_value = self.get_foreclosure_market_value()
        if foreclosure_market_value > 0:
            df.loc[df.date == self.foreclosure_date, 'foreclosure_market_value'] = foreclosure_market_value

        # Populate cash flows from the stored dictionaries
        df['noi'] = df['date'].map(self.noi).fillna(0)
        df['capex'] = df['date'].map(self.capex).fillna(0)

        # Adjust NOI and Capex when either is 0
        df.loc[df['noi'] == 0, 'noi'] = df['market_value'] * self.cap_rate / 12
        df.loc[df['capex'] == 0, 'capex'] = df['market_value'] * self.cap_rate / 12 * self.capex_percent_of_noi

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

    def concat_loan_schedules_at_share_df(self):
        if len(self.loans) == 0:
            return None
        else:
            self.check_loan_dates()
            loans_ = [loan.generate_loan_schedule_df() for loan in self.loans.values()]
            df = pd.concat(loans_)
            df['encumbered'] = df['encumbered'] > 0

            ownership_series = pd.DataFrame(
                list(self.generate_ownership_series().items()),
                columns=['date', 'ownership_share']
            )

            # Ensure dates are `date` objects
            df['date'] = df['date'].apply(lambda x: x.date() if isinstance(x, datetime) else x)
            ownership_series['date'] = ownership_series['date'].apply(lambda x: x.date() if isinstance(x, datetime) else x)

            # Merge ownership series with cash flows
            adjusted_cash_flows = df.merge(ownership_series, on='date', how='left')

            exclude_columns = {'ownership_share'}

            numeric_columns = adjusted_cash_flows.select_dtypes(include='number').columns
            for col in numeric_columns:
                if col not in exclude_columns:
                    adjusted_cash_flows[col] *= adjusted_cash_flows['ownership_share']

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
            #loan_values = self.combine_loan_values_df()
            #loan_values['date'] = pd.to_datetime(loan_values['date'])
            cash_flows = cash_flows.merge(loan_cash_flows, on='date',how='left')
            #cash_flows = cash_flows.merge(loan_values[['date','loan_value']], on='date', how='left')
            cash_flows['encumbered'] = cash_flows['encumbered']==True
        cash_flows.fillna(0, inplace=True)
        cash_flows['Property Name'] = self.name
        cash_flows['Property Type'] = self.property_type
        if self.encumbered == True:
            cash_flows['encumbered'] = True
        cash_flows['market_value_change'] = cash_flows['market_value'].diff()
        cash_flows['gain_loss'] = cash_flows['market_value_change'] - cash_flows['capex'] - cash_flows['partner_buyout_cost'] + cash_flows[
            'disposition_price'] - cash_flows['acquisition_cost'] + cash_flows['partial_sale_proceeds'] + cash_flows['foreclosure_market_value']
        cash_flows['gross_income'] = cash_flows['noi'] - cash_flows.get('interest_payment', 0)
        return cash_flows

    def calculate_effective_share(self, date_, nav):
        df = self.promote_cash_flows.copy()
        df['date'] = df['date'].apply(lambda x: self.ensure_date(x))
        date_ = self.ensure_date(date_)
        df['cash_flow'] = df['cash_flow'].astype(float)
        if date_ in df['date'].values:
            df.loc[df['date'] == date_, 'cash_flow'] += float(nav)
        else:
            new_row = pd.DataFrame({'date': [date_], 'cash_flow': [nav]})
            df = pd.concat([df, new_row], ignore_index=True)

        df = df.groupby('date').sum().reset_index()
        df = df.sort_values(by='date').reset_index(drop=True)
        df = df.loc[df.cash_flow != 0]
        df = df.loc[df.date <= date_]
        dates_ = df['date'].tolist()
        cfs = df['cash_flow'].tolist()

        if self.upper_tier_share:
            lp_effective_share = CarriedInterest(dates_, cfs, self.tiers).get_lp_effective_share() * self.upper_tier_share
        else:
            lp_effective_share = CarriedInterest(dates_, cfs, self.tiers).get_lp_effective_share()

        return lp_effective_share

    def calculate_effective_shares(self):
        df = self.combine_loan_cash_flows_df()
        df['date'] = df['date'].apply(lambda x: self.ensure_date(x))
        df['nav'] = df['market_value'] - df.get('ending_balance', 0)

        # Aggregate NAV by date to avoid duplicate processing
        aggregated = df.groupby('date')['nav'].sum().reset_index()

        # Calculate effective share for each unique date
        aggregated['effective_share'] = aggregated.apply(
            lambda row: self.calculate_effective_share(row['date'], row['nav']), axis=1
        )

        self.effective_shares = aggregated.set_index('date')['effective_share'].to_dict()
        return self.effective_shares

    def get_effective_share_by_month(self, date_):
        if not self.effective_shares:
            self.calculate_effective_shares()
        return self.effective_shares.get(date_)

    def adjust_cash_flows_by_ownership_df(self):
        """Adjust all numeric cash flow columns by the ownership share."""
        cash_flows = self.combine_loan_cash_flows_df()

        # Generate the ownership time series
        ownership_series = pd.DataFrame(
            list(self.generate_ownership_series().items()),
            columns=['date', 'ownership_share']
        )

        # Ensure dates are `date` objects
        cash_flows['date'] = cash_flows['date'].apply(lambda x: x.date() if isinstance(x, datetime) else x)
        ownership_series['date'] = ownership_series['date'].apply(lambda x: x.date() if isinstance(x, datetime) else x)

        # Merge ownership series with cash flows
        adjusted_cash_flows = cash_flows.merge(ownership_series, on='date', how='left')

        # Fill missing ownership shares with zero
        adjusted_cash_flows['ownership_share'] = adjusted_cash_flows['ownership_share'].fillna(0)

        # Filter out rows before acquisition date
        if self.acquisition_date:
            adjusted_cash_flows = adjusted_cash_flows[adjusted_cash_flows['date'] >= self.acquisition_date]

        # Avoid multiplying specific columns
        exclude_columns = {'partner_buyout_cost', 'partial_sale_proceeds', 'ownership_share'}

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
        if self.promote:
            adjusted_cash_flows = self.calculate_income_and_gain_loss(adjusted_cash_flows)
        adjusted_cash_flows.loc[adjusted_cash_flows['ownership_share'] == 1, 'effective_share'] = 1.0

        return adjusted_cash_flows

    def get_unencumbered_noi(self, beg_date: date, end_date: date):
        # Combine loan and property cash flows
        df = self.combine_loan_cash_flows_df()

        # Filter DataFrame by date range
        df = df[(df['date'] >= beg_date) & (df['date'] <= end_date)]

        # Calculate unencumbered NOI
        unencumbered_noi = df.loc[df['encumbered'] == False, 'noi'].sum()

        return unencumbered_noi

    def concat_loan_values_df(self, treasury_rates, chatham_style=True):
        if len(self.loans) == 0:
            return pd.DataFrame(columns=['loan_id', 'date', 'loan_value','discount_rate'])
        else:
            loan_values = []
            for loan in self.loans.values():
                for month_ in self.month_list:
                    loan_value = loan.value_loan(month_, treasury_rates, chatham_style)
                    loan_values.append((loan.id,month_,loan_value[0], loan_value[1]))
        df = pd.DataFrame(loan_values, columns=['loan_id', 'date', 'loan_value', 'discount_rate'])
        return df

    def combine_loan_values_df(self):
        if len(self.loans) == 0:
            return pd.DataFrame(columns=['loan_id', 'date', 'loan_value','discount_rate'])
        if not self.treasury_rates:
            raise ValueError("Treasury rates are not available.")
        df = self.concat_loan_values_df(self.treasury_rates, True)
        df = df.groupby('date')['loan_value'].sum().reset_index()
        return df

    def calculate_income_and_gain_loss(self, df):
        df['gain_loss_dilution'] = df.apply(lambda x: self.get_effective_share_adjustment(x['gain_loss'], x['ownership_share'], self.get_effective_share_by_month(x['date'])), axis=1)
        df['nav'] = df['market_value'] - df['ending_balance']
        df['gross_income_loss_dilution'] = df.apply(
            lambda x: self.get_effective_share_adjustment(x['gross_income'], x['ownership_share'],
                                                          self.get_effective_share_by_month(x['date'])), axis=1)
        df['nav_dilution'] = df.apply(lambda x: self.get_effective_share_adjustment(x['nav'], x['ownership_share'],
                                                          self.get_effective_share_by_month(x['date'])), axis=1)
        df['effective_share'] = df['date'].apply(lambda x: self.get_effective_share_by_month(x))
        return df

    def capitalize_forward_noi(self, date_, cap_rate):
        noi_sums = []
        start_date = date_
        for _ in range(12):
            next_month = self.ensure_date(start_date + relativedelta(months=1))
            monthly_sum = sum(
                value for date, value in self.noi.items()
                if start_date <= date < next_month
            )
            noi_sums.append(monthly_sum)
            start_date = next_month
        return sum(noi_sums) / cap_rate

    def get_effective_share_adjustment(self, stated_value, stated_share, effective_share):

        if stated_share == 0:
            return 0
        elif stated_share < 1:
            effective_value = stated_value / stated_share * effective_share
            return effective_value - stated_value
        return 0

    def calculate_exit_value(self, disposition_date=None):
        if disposition_date is None:
            disposition_date = self.disposition_date

        disposition_index = self.month_list.index(disposition_date)

        next_twelve_noi = 0
        # Loop only within valid indices
        for i in range(disposition_index + 1, min(disposition_index + 13, len(self.month_list))):
            noi_month = self.month_list[i]
            next_twelve_noi += self.get_noi(noi_month)

        return next_twelve_noi / 0.05

    def calculate_property_irr(self, disposition_date=None):
        if disposition_date is None:
            disposition_date = self.disposition_date
        disposition_index = self.month_list.index(disposition_date)
        irr_months = self.month_list[:disposition_index+1]
        cash_flows = []
        cash_flows.append(-self.market_value)
        for month in irr_months:
            sale_proceeds = self.calculate_exit_value(disposition_date) if disposition_date == month else 0
            cash_flow = self.get_noi(month) - self.get_capex(month) + sale_proceeds
            cash_flows.append(cash_flow)
        irr = npf.irr(cash_flows)*12
        return irr, cash_flows

    def find_optimal_disposition_date(self):
        # Ensure at least one year of cash flows
        min_months = 12

        # Initialize variables to track the best IRR and corresponding disposition date
        max_irr = float('-inf')
        optimal_date = None
        best_cash_flows = []

        # Iterate through potential disposition dates starting from month 13
        for i in range(min_months, len(self.month_list)):
            disposition_date = self.month_list[i]

            # Calculate IRR for this disposition date
            irr, cash_flows = self.calculate_property_irr(disposition_date)

            # Update the optimal date if the IRR is higher
            if irr > max_irr:
                max_irr = irr
                optimal_date = disposition_date
                best_cash_flows = cash_flows

        return optimal_date, max_irr, best_cash_flows
