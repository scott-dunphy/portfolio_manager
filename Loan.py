import pandas as pd
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from collections import OrderedDict
from typing import Optional
import logging
from .LoanValuation import LoanValuation


class Loan:
    def __init__(self,
                 id: str,
                 loan_amount: float,
                 rate: float,
                 fund_date: date,
                 maturity_date: date,
                 payment_type: str,
                 property_id: Optional[str] = None,
                 interest_only_periods: Optional[int] = 0,
                 amortizing_periods: Optional[int] = 360,
                 commitment: Optional[float] = None,
                 prepayment_date: Optional[date] = None,
                 foreclosure_date: Optional[date] = None,
                 market_rate: Optional[float] = None,
                 fixed_floating: Optional[str] = None,):
        # Configure logging
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.WARNING)

        if loan_amount < 0:
            raise ValueError("Loan amount must be positive.")
        if rate < 0 or rate > 1:
            raise ValueError("Rate must be between 0 and 1.")
        if fund_date >= maturity_date:
            raise ValueError("Funding date must precede maturity date.")
        if payment_type not in ['Actual/360', '30/360', 'Actual/365']:
            raise ValueError(f"Unsupported payment type: {payment_type}")

        self.id = id
        self.property_id = str(property_id) if property_id else None
        self.loan_amount = loan_amount
        self.rate = rate
        self.fund_date = self.get_end_of_month(fund_date)
        self.fund_date_actual = fund_date
        self.maturity_date = self.get_end_of_month(maturity_date)
        self.payment_type = payment_type
        self.interest_only_periods = interest_only_periods
        self.fixed_floating = fixed_floating
        self.amortizing_periods = amortizing_periods
        self.amortizing_payment = self.calculate_amortizing_payment(loan_amount)
        self.market_rate = market_rate if market_rate else None
        self.schedule = self.initialize_loan_schedule()
        self.loan_draws = self.initialize_monthly_activity()
        self.loan_paydowns = self.initialize_monthly_activity()
        self.commitment = commitment or None
        self.foreclosure_date = self.get_end_of_month(foreclosure_date) if foreclosure_date else None
        self.calculate_unfunded()

        # Safely handle prepayment_date
        if prepayment_date is not None and not pd.isna(prepayment_date):
            self.prepayment_date = self.get_end_of_month(prepayment_date)
        else:
            self.prepayment_date = None

    def get_end_of_month(self, input_date: date) -> Optional[date]:
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

    def get_prior_month(self, input_date: date) -> date:
        """Returns the last day of the prior month."""
        prior_month = input_date - relativedelta(months=1)
        return prior_month.replace(day=monthrange(prior_month.year, prior_month.month)[1])

    def get_commitment(self):
        return self.commitment

    def initialize_unfunded_schedule(self):
        """Create an initial unfunded schedule based on the commitment."""
        if not self.commitment:
            self.unfunded = OrderedDict({month: 0 for month in self.monthly_dates})
            return

        # Initialize with full commitment at the start
        unfunded = OrderedDict()
        for month in self.monthly_dates:
            if month < self.fund_date:
                unfunded[month] = 0  # No commitment before funding date
            elif month == self.fund_date:
                unfunded[month] = self.commitment - self.loan_amount
            else:
                unfunded[month] = self.commitment

        self.unfunded = unfunded

    def adjust_unfunded_schedule(self):
        """Adjust the unfunded schedule based on draws and paydowns."""
        if not self.commitment:
            return

        for i, month in enumerate(self.monthly_dates):
            if i == 0:
                # Initial funding month
                self.unfunded[month] = max(
                    0,
                    self.unfunded[month] - self.loan_draws[month] + self.loan_paydowns[month]
                )
            else:
                # Adjust unfunded based on prior month, current draws, and paydowns
                prior_month = self.get_prior_month(month)
                self.unfunded[month] = max(
                    0,
                    self.unfunded[prior_month]
                    - self.loan_draws[month]
                    + self.loan_paydowns[month]
                )

    def calculate_unfunded(self):
        """Calculate the unfunded commitment schedule."""
        # Step 1: Initialize the baseline schedule
        self.initialize_unfunded_schedule()

        # Step 2: Adjust based on draws and paydowns
        self.adjust_unfunded_schedule()

    def calculate_interest(self, balance: float, start_date: date, end_date: date) -> float:
        date_delta = (end_date - start_date).days
        payment_type_numerators = {'Actual/360': date_delta, '30/360': 30, 'Actual/365': date_delta}
        payment_type_denominators = {'Actual/360': 360, '30/360': 360, 'Actual/365': 365}
        payment_type_numerator = payment_type_numerators[self.payment_type]
        payment_type_denominator = payment_type_denominators[self.payment_type]
        return balance * self.rate * payment_type_numerator / payment_type_denominator

    def calculate_amortizing_payment(self, loan_balance):
        if self.amortizing_periods == 0:
            return 0
        # Convert annual rate to monthly rate
        monthly_rate = self.rate / 12
        # Total number of payments
        total_payments = self.amortizing_periods

        # Amortizing payment formula
        if monthly_rate == 0:  # Handle zero-interest loans
            return loan_balance / total_payments
        else:
            return loan_balance * (monthly_rate * (1 + monthly_rate) ** total_payments) / (
                    (1 + monthly_rate) ** total_payments - 1)

    def initialize_monthly_activity(self) -> OrderedDict:
        return OrderedDict({
            month: 0 for month in self.monthly_dates
        })

    def add_loan_draw(self, draw: float, draw_date: date):
        draw_date = self.get_end_of_month(draw_date)
        if self.get_commitment():
            prior_month = self.get_prior_month(draw_date)
            allowable_draw = self.unfunded.get(prior_month)
            #print(f"{self.id}: {allowable_draw}")
            allowable_draw = allowable_draw if allowable_draw is not None else 0
            draw = min(draw, allowable_draw)
            if draw > 0:
                self.loan_draws[draw_date] = draw
                self.calculate_unfunded()
                self.generate_loan_schedule()
                return draw
            else:
                self.logger.warning(f"{self.id}: No available commitment to draw on {draw_date}.")
                return 0
        self.logger.warning("No commitment set for the loan.")
        return 0

    def add_loan_paydown(self, paydown: float, paydown_date: date):
        paydown_date = self.get_end_of_month(paydown_date)
        self.generate_loan_schedule()
        if paydown_date not in self.schedule:
            self.logger.warning(f"Paydown date {paydown_date} is not in the loan schedule.")
            return  # Alternatively, raise an exception

        # Calculate the allowable paydown: beginning_balance + loan_draw for the month
        beginning_balance = self.schedule[paydown_date]['beginning_balance']
        loan_draw = self.schedule[paydown_date]['loan_draw']
        allowable_paydown = beginning_balance + loan_draw

        if paydown > allowable_paydown:
            self.logger.warning(
                f"Attempted paydown of {paydown:.2f} on {paydown_date} exceeds the allowable amount of {allowable_paydown:.2f}. "
                f"Paydown will be limited to {allowable_paydown:.2f}."
            )
            paydown = allowable_paydown

        # Apply paydown without regenerating the entire schedule
        existing_paydown = self.loan_paydowns.get(paydown_date, 0)
        total_paydown = existing_paydown + paydown

        # Ensure total paydown does not exceed allowable amount
        if total_paydown > allowable_paydown:
            self.logger.warning(
                f"Total paydown of {total_paydown:.2f} on {paydown_date} exceeds the allowable amount of {allowable_paydown:.2f}. "
                f"Paydown will be limited to {allowable_paydown - existing_paydown:.2f}."
            )
            paydown = allowable_paydown - existing_paydown
            total_paydown = existing_paydown + paydown

        self.loan_paydowns[paydown_date] = total_paydown

        # Update the loan schedule directly
        self.schedule[paydown_date]['loan_paydown'] = total_paydown
        self.schedule[paydown_date]['ending_balance'] = (
                self.schedule[paydown_date]['beginning_balance'] +
                self.schedule[paydown_date]['loan_draw'] -
                self.schedule[paydown_date]['loan_paydown'] -
                self.schedule[paydown_date]['scheduled_principal_payment']
        )

        # **Recalculate Unfunded Commitment**
        self.calculate_unfunded()

        # **Regenerate the Schedule to Reflect the Updated Unfunded Commitment**
        self.generate_loan_schedule()

    def get_loan_draw(self, draw_date: date):
        return self.loan_draws.get(draw_date, 0)

    def get_loan_paydown(self, paydown_date: date):
        return self.loan_paydowns.get(paydown_date, 0)

    def initialize_loan_schedule(self) -> OrderedDict:
        """Initialize the loan schedule as an ordered dictionary."""
        self.monthly_dates = [
            self.get_end_of_month(self.fund_date + relativedelta(months=i))
            for i in range(
                (self.maturity_date.year - self.fund_date.year) * 12 +
                self.maturity_date.month - self.fund_date.month + 1
            )
        ]
        return OrderedDict({
            month: {
                'beginning_balance': 0,
                'loan_draw': 0,
                'loan_paydown': 0,
                'interest_payment': 0,
                'scheduled_principal_payment': 0,
                'ending_balance': 0,
                'encumbered': 1
            } for month in self.monthly_dates
        })

    def get_scheduled_principal_payment(self, period, amortizing_payment, interest_payment):
        if period <= self.interest_only_periods:
            return 0
        return amortizing_payment - interest_payment

    def generate_loan_schedule(self) -> OrderedDict:
        prior_key = self.fund_date
        prepayment_done = False

        for i, key in enumerate(self.schedule.keys()):
            # Foreclosure Check
            if self.foreclosure_date and key >= self.foreclosure_date:
                self.schedule[key].update({
                    'beginning_balance': 0,
                    'loan_draw': 0,
                    'loan_paydown': 0,
                    'interest_payment': 0,
                    'scheduled_principal_payment': 0,
                    'ending_balance': 0,
                    'encumbered': 0
                })
                continue

            # Initialize first period
            if i == 0:
                self.schedule[key]['beginning_balance'] = 0
                self.schedule[key]['loan_draw'] = self.loan_amount  # Loan draw on funding date
                self.schedule[key]['loan_paydown'] = self.get_loan_paydown(key)
                self.schedule[key]['interest_payment'] = 0
                self.schedule[key]['scheduled_principal_payment'] = 0
                self.schedule[key]['ending_balance'] = self.loan_amount - self.schedule[key]['loan_paydown']
            else:
                # Zero out all cash flows after prepayment is done and balance is zero
                if prepayment_done and self.schedule[prior_key]['ending_balance'] <= 0:
                    self.schedule[key].update({
                        'beginning_balance': 0,
                        'loan_draw': 0,
                        'loan_paydown': 0,
                        'interest_payment': 0,
                        'scheduled_principal_payment': 0,
                        'ending_balance': 0,
                        'encumbered': 0
                    })
                    continue

                # Normal Loan Calculations Before Prepayment or Full Amortization
                beginning_balance = self.schedule[prior_key]['ending_balance']
                self.schedule[key]['beginning_balance'] = max(0, beginning_balance)
                self.schedule[key]['loan_draw'] = self.get_loan_draw(key)
                self.schedule[key]['loan_paydown'] = self.get_loan_paydown(key)

                # Calculate interest
                self.schedule[key]['interest_payment'] = self.calculate_interest(
                    self.schedule[key]['beginning_balance'], prior_key, key
                )

                # Scheduled Principal Payment (Only if Amortizing)
                if self.amortizing_periods > 0 and i > self.interest_only_periods:
                    scheduled_principal = max(
                        0, self.amortizing_payment - self.schedule[key]['interest_payment']
                    )
                    # Avoid overpaying past zero balance
                    scheduled_principal = min(
                        scheduled_principal, self.schedule[key]['beginning_balance']
                    )
                    self.schedule[key]['scheduled_principal_payment'] = scheduled_principal
                else:
                    self.schedule[key]['scheduled_principal_payment'] = 0

                # Prepayment Check Without Double-Counting Scheduled Principal
                if self.prepayment_date and key == self.prepayment_date and not prepayment_done:
                    # Calculate prepayment amount after applying scheduled principal payment
                    prepayment_amount = max(
                        0, self.schedule[key]['beginning_balance'] -
                           self.schedule[key]['scheduled_principal_payment']
                    )
                    # Directly set the paydown without calling add_loan_paydown
                    allowable_paydown = self.schedule[key]['beginning_balance'] + self.schedule[key]['loan_draw']
                    if prepayment_amount > allowable_paydown:
                        self.logger.warning(
                            f"Attempted prepayment of {prepayment_amount:.2f} on {key} exceeds the allowable amount of {allowable_paydown:.2f}. "
                            f"Prepayment will be limited to {allowable_paydown:.2f}."
                        )
                        prepayment_amount = allowable_paydown
                    self.loan_paydowns[key] = prepayment_amount
                    self.schedule[key]['loan_paydown'] = prepayment_amount
                    prepayment_done = True

                # Apply maturity paydown if the loan matures and prepayment hasn't been done
                if key == self.maturity_date and not prepayment_done:
                    maturity_paydown = max(
                        0, self.schedule[key]['beginning_balance'] -
                           self.schedule[key]['scheduled_principal_payment']
                    )
                    # Directly set the paydown without calling add_loan_paydown
                    allowable_paydown = self.schedule[key]['beginning_balance'] + self.schedule[key]['loan_draw']
                    if maturity_paydown > allowable_paydown:
                        self.logger.warning(
                            f"Attempted maturity paydown of {maturity_paydown:.2f} on {key} exceeds the allowable amount of {allowable_paydown:.2f}. "
                            f"Maturity paydown will be limited to {allowable_paydown:.2f}."
                        )
                        maturity_paydown = allowable_paydown
                    self.loan_paydowns[key] = maturity_paydown
                    self.schedule[key]['loan_paydown'] = maturity_paydown

                # Update ending balance
                self.schedule[key]['ending_balance'] = max(
                    0, self.schedule[key]['beginning_balance'] +
                       self.schedule[key]['loan_draw'] -
                       self.schedule[key]['loan_paydown'] -
                       self.schedule[key]['scheduled_principal_payment']
                )

            prior_key = key

        return self.schedule

    def generate_loan_schedule_df(self):
        df = pd.DataFrame.from_dict(self.generate_loan_schedule()).T
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'date'}, inplace=True)
        df['fixed_floating'] = self.fixed_floating
        return df

    def calculate_loan_market_value(self, as_of_date: date, discount_rate: Optional[float] = None):
        as_of_date = self.get_end_of_month(as_of_date)
        if discount_rate is None:
            discount_rate = self.rate

        # Generate the loan schedule
        schedule_df = self.generate_loan_schedule_df()

        # Ensure schedule_df has required columns
        required_columns = {'date', 'interest_payment', 'scheduled_principal_payment', 'loan_draw'}
        if not required_columns.issubset(schedule_df.columns):
            raise ValueError(
                f"Loan schedule is missing required columns: {required_columns - set(schedule_df.columns)}")

        # Filter schedule to only include cash flows after the as_of_date
        schedule_df = schedule_df[schedule_df['date'] > as_of_date]

        # Calculate present value of cash flows
        market_value = 0.0
        for _, row in schedule_df.iterrows():
            cash_flow_date = row['date']
            interest_payment = row['interest_payment']
            principal_payment = row['scheduled_principal_payment']
            loan_draw = row['loan_draw']
            loan_paydown = row['loan_paydown']

            # Total cash flow for the period: loan draws, interest payments, and principal payments
            cash_flow = interest_payment + principal_payment + loan_paydown - loan_draw

            # Calculate the number of periods (months) from the as_of_date to the cash flow date
            months_elapsed = (cash_flow_date.year - as_of_date.year) * 12 + (cash_flow_date.month - as_of_date.month)

            # Discount the cash flow to present value
            discounted_cash_flow = cash_flow / ((1 + discount_rate / 12) ** months_elapsed)

            # Accumulate the discounted cash flow
            market_value += discounted_cash_flow

        return market_value

    def value_loan(self, as_of_date, treasury_rates: dict, chatham_style=True):
        print(self.market_rate)
        valuer = LoanValuation(self.fund_date_actual, self.rate, treasury_rates)
        loan_schedule = self.generate_loan_schedule_df()
        max_date = loan_schedule['date'].max()
        if max_date <= as_of_date:
            logging.warning(f"{self.id}: Loan cash flows end before as of date.")
            return 0,0
        if self.market_rate:
            market_value = valuer.calculate_loan_market_value(as_of_date, loan_schedule, chatham_style, discount_rate=self.market_rate)
            market_rate = self.market_rate
            self.spread = 0
        else:
            market_value = valuer.calculate_loan_market_value(as_of_date, loan_schedule, chatham_style)
            market_rate = valuer.discount_rate
            self.spread = valuer.spread

        return market_value, market_rate

