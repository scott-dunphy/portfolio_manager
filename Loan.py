import pandas as pd
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from collections import OrderedDict
from typing import Optional
import pandas as pd
class Loan:
    def __init__(self,
                 id: str,
                 loan_amount: float,
                 rate: float,
                 fund_date: date,
                 maturity_date: date,
                 payment_type: str,
                 property_id: Optional[str] = None,
                 interest_only_periods: Optional[int]=0,
                 amortizing_periods: Optional[int]=360,
                 commitment: Optional[float] = None,
                 prepayment_date: Optional[date] = None,
                 foreclosure_date: Optional[date] = None):
        if loan_amount < 0:
            raise ValueError("Loan amount must be positive.")
        if rate < 0 or rate > 1:
            raise ValueError("Rate must be between 0 and 1.")
        if fund_date >= maturity_date:
            raise ValueError("Funding date must precede maturity date.")
        if payment_type not in ['Actual/360', '30/360', 'Actual/365']:
            raise ValueError(f"Unsupported payment type: {payment_type}")
        self.id = id
        self.property_id = str(property_id)
        self.loan_amount = loan_amount
        self.rate = rate
        self.fund_date = self.get_end_of_month(fund_date)
        self.maturity_date = self.get_end_of_month(maturity_date)
        self.payment_type = payment_type
        self.interest_only_periods = interest_only_periods
        self.amortizing_periods = amortizing_periods
        self.amortizing_payment = self.calculate_amortizing_payment(loan_amount)
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

    def get_end_of_month(self, input_date: date) -> date:
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
        return prior_month.replace(day=1) + relativedelta(day=31)

    def get_commitment(self):
        return self.commitment

    def calculate_unfunded(self):
        if self.commitment:
            self.loan_draws[self.fund_date] = self.loan_amount
            unfunded = self.initialize_monthly_activity()
            i=0
            for month,value in unfunded.items():
                if i==0:
                    unfunded[month] = self.get_commitment() - self.get_loan_draw(month) + self.get_loan_paydown(month)
                else:
                    prior_month = self.get_prior_month(month)
                    unfunded[month] = unfunded[prior_month] - self.get_loan_draw(month) + self.get_loan_paydown(month)
                i += 1
            self.unfunded = unfunded
            return unfunded
        return
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
        # Convert annual rate to monthly rate)
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
            month:0 for month in self.monthly_dates
        })

    def add_loan_draw(self, draw: float, draw_date: date):
        if self.get_commitment():
            prior_month = self.get_prior_month(draw_date)
            draw = min(draw, self.unfunded[prior_month])
            self.loan_draws[draw_date] = draw
            self.calculate_unfunded()
            self.generate_loan_schedule()
            return draw

    def add_loan_paydown(self, paydown: float, paydown_date: date):
        if paydown_date in self.schedule:
            # Apply paydown without regenerating the entire schedule
            paydown = min(paydown, self.schedule[paydown_date]['beginning_balance'])
            self.loan_paydowns[paydown_date] = paydown

            # Update the loan schedule directly
            self.schedule[paydown_date]['loan_paydown'] = paydown
            self.schedule[paydown_date]['ending_balance'] = (
                self.schedule[paydown_date]['beginning_balance'] - paydown
            )

    def get_loan_draw(self, draw_date: date):
        return self.loan_draws[draw_date]

    def get_loan_paydown(self, paydown_date: date):
        return self.loan_paydowns[paydown_date]

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
                self.schedule[key]['loan_paydown'] = 0
                self.schedule[key]['interest_payment'] = 0
                self.schedule[key]['scheduled_principal_payment'] = 0
                self.schedule[key]['ending_balance'] = self.loan_amount  # Ending balance reflects the draw
            else:
                if prepayment_done or self.schedule[prior_key]['ending_balance'] <= 0:
                    # Zero out all cash flows after prepayment or full amortization
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
                self.schedule[key]['beginning_balance'] = max(0, self.schedule[prior_key]['ending_balance'])
                self.schedule[key]['loan_draw'] = self.get_loan_draw(key)
                self.schedule[key]['loan_paydown'] = max(0, self.get_loan_paydown(key))

                # Calculate interest
                self.schedule[key]['interest_payment'] = self.calculate_interest(
                    self.schedule[key]['beginning_balance'], prior_key, key
                )

                # **Scheduled Principal Payment (Only if Amortizing)**
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

                # **Prepayment Check Without Double-Counting Scheduled Principal**
                if self.prepayment_date and key == self.prepayment_date and not prepayment_done:
                    # Calculate prepayment amount after applying scheduled principal payment
                    prepayment_amount = max(
                        0, self.schedule[key]['beginning_balance'] -
                           self.schedule[key]['scheduled_principal_payment']
                    )
                    self.add_loan_paydown(prepayment_amount, key)
                    prepayment_done = True

                # Apply maturity paydown if the loan matures
                if key == self.maturity_date and not prepayment_done:
                    maturity_paydown = max(
                        0, self.schedule[key]['beginning_balance'] -
                           self.schedule[key]['scheduled_principal_payment']
                    )
                    self.add_loan_paydown(maturity_paydown, key)

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
        df.rename(columns={'index':'date'},inplace=True)
        return df





