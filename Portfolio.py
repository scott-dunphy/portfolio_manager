from .Property import Property
from .Loan import Loan
import pandas as pd
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from collections import OrderedDict
from typing import Optional
import pandas as pd
import logging

class Portfolio:
    def __init__(self,

                 ):

        self.properties = {}  # Key: Property ID, Value: Property instance
        self.loans = {}
        self.analysis_start_date = date(2024,10,1)
        self.analysis_end_date = date(2026,10,1)
        self.beginning_cash = 0
        self.capital_calls = {}
        self.redemptions = {}
        self.distributions = {}
        self.loan_capital = {
            'Apartment': 200,
            'Office': 0.15,
            'Retail': 0.20,
            'Industrial': 0.10,
                             }

    def set_file_path(self, file_path):
        self.file_path = file_path

    def get_loan_capital(self, building_size, property_type):
        return building_size * self.loan_capital.get(property_type)

    def get_loan_capital_df(self):
        loan_capital = []
        for property in self.properties.values():
            capital = self.get_loan_capital(property.building_size, property.property_type)
            loan_capital.append((property.name, capital))
        return pd.DataFrame(loan_capital,columns=['Property Name','loan_capital'])

    def load_data(self):
        self.load_properties()
        self.load_cash_flows()
        self.load_property_loans()
        self.load_unsecured_loans()
        self.load_unsecured_loan_flows()
        self.load_capital_flows()
        for property in self.properties.values():
            property.calculate_unfunded_equity()



    def read_import_file(self, sheet_name):
        df = pd.read_excel(self.file_path, sheet_name=sheet_name, dtype={'id': str})
        date_columns = ['acquisition_date', 'disposition_date', 'date', 'fund_date', 'maturity_date', 'prepayment_date','foreclosure_date']  # Replace with your actual date column names
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.date
        return df

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

    def load_properties(self, df: Optional[pd.DataFrame] = None):
        if df is None:
            df = self.read_import_file('Properties')
        df['id'] = df['id'].fillna('').astype(str)
        #df = pd.read_excel(self.file_path, sheet_name='Properties', dtype={'id':str})
        for i,row in df.iterrows():
            self.add_property(
                Property(
                    id=row['id'],
                    name=row['name'],
                    property_type=row['property_type'],
                    acquisition_date=self.ensure_date(row['acquisition_date']),
                    disposition_date=self.ensure_date(row['disposition_date']),
                    acquisition_cost=row['acquisition_cost'],
                    disposition_price=row['disposition_price'],
                    address=row['address'],
                    city=row['city'],
                    state=row['state'],
                    zipcode=row['zipcode'],
                    building_size=row['building_size'],
                    market_value=row['market_value'],
                    analysis_date=row['analysis_date'],
                    analysis_length=row['analysis_length'],
                    loans = {},
                    market_value_growth=row['market_value_growth'],
                    ownership=row['ownership'],
                    construction_end=self.ensure_date(row['construction_end']),
                    equity_commitment=row['equity_commitment'],
                    partner_buyout_cost=row['partner_buyout_cost'],
                    partner_buyout_date=self.ensure_date(row['partner_buyout_date']),
                    partner_buyout_percent=row['partner_buyout_percent'],
                    partial_sale_date=self.ensure_date(row['partial_sale_date']),
                    partial_sale_percent=row['partial_sale_percent'],
                    partial_sale_proceeds=row['partial_sale_proceeds'],
                    encumbered=row['encumbered']
                )
            )
        return df

    def load_cash_flows(self, df: Optional[pd.DataFrame] = None):
        if df is None:
            df = self.read_import_file('Cash Flows')

        # Ensure proper data types and valid dates
        df['id'] = df['id'].fillna('').astype(str)
        df['date'] = df['date'].apply(lambda x: self.ensure_date(x))

        # Iterate through properties and update their cash flows
        for prop_id, property in self.properties.items():
            # Create dictionaries for cash flows ensuring dates are date objects
            noi = dict(zip(
                df.loc[(df['cash_flow'] == 'noi') & (df['id'] == prop_id), 'date'].apply(self.ensure_date),
                df.loc[(df['cash_flow'] == 'noi') & (df['id'] == prop_id), 'amount']
            ))

            capex = dict(zip(
                df.loc[(df['cash_flow'] == 'capex') & (df['id'] == prop_id), 'date'].apply(self.ensure_date),
                df.loc[(df['cash_flow'] == 'capex') & (df['id'] == prop_id), 'amount']
            ))

            # Update the properties with cash flows
            property.update_noi(noi)
            property.update_capex(capex)

    def load_capital_flows(self, df: Optional[pd.DataFrame] = None):
        if df is None:
            df = self.read_import_file('Capital Flows')
        df['date'] = df['date'].apply(lambda x: self.ensure_date(x))
        capital_calls = dict(zip(
            df.loc[(df['cash_flow'] == 'capital call'), 'date'].apply(self.ensure_date),
            df.loc[(df['cash_flow'] == 'capital call'), 'amount']
        ))

        redemptions = dict(zip(
            df.loc[(df['cash_flow'] == 'redemption'), 'date'].apply(self.ensure_date),
            df.loc[(df['cash_flow'] == 'redemption'), 'amount']
        ))

        distributions = dict(zip(
            df.loc[(df['cash_flow'] == 'distribution'), 'date'].apply(self.ensure_date),
            df.loc[(df['cash_flow'] == 'distribution'), 'amount']
        ))
        self.capital_calls = capital_calls
        self.redemptions = redemptions
        self.distributions = distributions


    def load_property_loans(self, df: Optional[pd.DataFrame] = None):
        if df is None:
            df = self.read_import_file('Secured Loans')
        #df = pd.read_excel(self.file_path, sheet_name="Secured Loans", dtype={'id': str, 'property_id': str})

        # Ensure IDs are strings and handle missing values
        df['id'] = df['id'].fillna('').astype(str)
        df['property_id'] = df['property_id'].fillna('').astype(str)

        for _, row in df.iterrows():
            # Create Loan instance
            loan = Loan(
                id=row['id'],
                property_id=row['property_id'],
                loan_amount=row['loan_amount'],
                rate=row['rate'],
                fund_date=row['fund_date'],
                maturity_date=row['maturity_date'],
                payment_type=row['payment_type'],
                interest_only_periods=row['interest_only_periods'],
                amortizing_periods=row['amortizing_periods'],
                commitment=row['commitment'],
                prepayment_date=row['prepayment_date'],
                foreclosure_date=row['foreclosure_date']
            )

            # Add loan to the corresponding property
            for property_id, property_ in self.properties.items():
                if loan.property_id == property_id:
                    property_.add_loan(loan)
                    print(f"Adding loan with ID {loan.id} to property {row['property_id']}")

    def load_unsecured_loans(self, df: Optional[pd.DataFrame] = None):
        if df is None:
            df = self.read_import_file('Unsecured Loans')
        df['id'] = df['id'].fillna('').astype(str)

        for _, row in df.iterrows():
            # Create Loan instance
            loan = Loan(
                id=row['id'],
                loan_amount=row['loan_amount'],
                rate=row['rate'],
                fund_date=row['fund_date'],
                maturity_date=row['maturity_date'],
                payment_type=row['payment_type'],
                interest_only_periods=row['interest_only_periods'],
                amortizing_periods=row['amortizing_periods'],
                commitment=row['commitment'],
                prepayment_date=row['prepayment_date'],
                foreclosure_date=row['foreclosure_date']
            )

            self.add_loan(loan)

    def load_unsecured_loan_flows(self, df: Optional[pd.DataFrame] = None):
        if df is None:
            df = self.read_import_file('Unsecured Loan Flows')
        df['id'] = df['id'].fillna('').astype(str)

        for _, row in df.iterrows():
            # Create Loan instance
            id = row['id']
            flow_type = row['flow_type']
            date_ = self.ensure_date(row['date'])
            amount = row['amount']
            if flow_type == 'draw':
                self.add_loan_draw(id,amount,date_)
            elif flow_type == 'paydown':
                self.add_loan_paydown(id, amount,date_)
            else:
                raise ValueError("No such flow type.")

    def add_property(self, property):
        self.properties[property.id] = property

    def remove_property(self, id):
        if id in self.properties:
            del self.properties[id]

    def get_property(self, id):
        if id in self.properties:
            return self.properties.get(id)

    def update_property(self, id, **kwargs):
        if id in self.properties:
            property = self.properties.get(id)
            for k,v in kwargs.items():
                setattr(property, k, v)

    def execute_property_func(self, property_id, func, *args, **kwargs):
        """
        Execute a method of the Property class and update it in the Portfolio.

        :param property_id: The ID of the property to update.
        :param func: The method of the Property class to execute.
        :param args: Positional arguments for the method.
        :param kwargs: Keyword arguments for the method.
        """
        property = self.get_property(property_id)
        if not property:
            raise KeyError(f"Property ID {property_id} not found.")

        # Execute the function on the property
        return func(property, *args, **kwargs)

    def update_noi(self, property_id, noi):
        self.execute_property_func(property_id, Property.update_noi, noi=noi)
        return

    def update_capex(self, property_id, capex):
        self.execute_property_func(property_id, Property.update_capex, capex=capex)
        return

    def update_market_value(self, property_id, market_value):
        self.execute_property_func(property_id, Property.update_market_value, market_value=market_value)
        return

    def get_property_cash_flow(self, property_id):
        return self.execute_property_func(property_id, Property.get_cash_flows)

    def add_loan(self, loan: Loan):
        if loan.id in self.loans:
            raise ValueError(f"Loan with ID {loan.id} already exists.")
        self.loans[loan.id] = loan

    def remove_loan(self, id):
        if id in self.loans:
            del self.loans[id]

    def get_loan(self, id):
        if id in self.loans:
            return self.loans.get(id)

    def update_loan(self, id, **kwargs):
        if id in self.loans:
            loan = self.loans.get(id)
            for k, v in kwargs.items():
                setattr(loan, k, v)
    def execute_loan_func(self, loan_id, func, *args, **kwargs):
        loan = self.get_loan(loan_id)
        if not loan:
            raise KeyError(f"loan ID {loan_id} not found.")

        # Execute the function on the loan
        return func(loan, *args, **kwargs)

    def add_loan_draw(self, loan_id: str, draw: float, draw_date: date):
        draw = self.execute_loan_func(loan_id, Loan.add_loan_draw, draw=draw, draw_date=draw_date)
        return draw

    def add_loan_paydown(self, loan_id: str, paydown: float, paydown_date: date):
        self.execute_loan_func(loan_id, Loan.add_loan_paydown, paydown=paydown, paydown_date=paydown_date)
        return

    def generate_loan_schedule_df(self, loan_id: str):
        df = self.execute_loan_func(loan_id, Loan.generate_loan_schedule_df)
        df['encumbered'] = False
        return df

    def combine_loan_schedules_df(self):
        loans_ = [loan.generate_loan_schedule_df() for loan in self.loans.values()]
        df = pd.concat(loans_)
        df = df.groupby('date').sum().reset_index()
        df['encumbered'] = False
        return df

    def concat_loan_schedules_df(self):
        loans_ = []
        for loan in self.loans.values():
            df = loan.generate_loan_schedule_df()
            df['loan_id'] = loan.id
            cols = df.columns[-1:].append(df.columns[:-1])
            loans_.append(df[cols])
        df = pd.concat(loans_)
        df['encumbered'] = False
        return df

    def concat_property_cash_flows(self):
        property_cash_flows = pd.concat([
            property.combine_loan_cash_flows_df()
            for property in list(self.properties.values()
                                 )])
        property_cash_flows['date'] = pd.to_datetime(property_cash_flows['date']).dt.date
        cols = list(property_cash_flows.columns[-2:].append(property_cash_flows.columns[0:-2]))
        property_cash_flows = property_cash_flows.fillna(0)
        return property_cash_flows[cols]

    def concat_property_cash_flows_at_share(self):
        property_cash_flows = pd.concat([
            property.adjust_cash_flows_by_ownership_df()
            for property in list(self.properties.values()
                                 )])
        property_cash_flows['date'] = pd.to_datetime(property_cash_flows['date']).dt.date
        cols = list(property_cash_flows.columns[-3:].append(property_cash_flows.columns[0:-3]))
        property_cash_flows = property_cash_flows.fillna(0)

        return property_cash_flows[cols]

    def concat_property_cash_flows_at_share_with_unsecured_loans(self):
        property_cash_flows = self.concat_property_cash_flows_at_share()
        unsecured_loan_cash_flows = self.concat_loan_schedules_df()
        unsecured_loan_cash_flows = unsecured_loan_cash_flows.loc[(unsecured_loan_cash_flows.date >= self.analysis_start_date) & (unsecured_loan_cash_flows.date <= self.analysis_end_date)]
        unsecured_loan_cash_flows['date'] = pd.to_datetime(unsecured_loan_cash_flows['date']).dt.date
        unsecured_loan_cash_flows.rename(columns={'loan_id':'Property Name'},inplace=True)
        unsecured_loan_cash_flows['Property Type'] = 'Fund-Level'
        portfolio_cash_flows = pd.concat([property_cash_flows, unsecured_loan_cash_flows], axis=0)

        loan_capital = self.get_loan_capital_df().drop_duplicates(subset=['Property Name'])
        portfolio_cash_flows = portfolio_cash_flows.merge(loan_capital, how='left', on='Property Name')
        portfolio_cash_flows['loan_capital'] = portfolio_cash_flows['ownership_share'] * portfolio_cash_flows[
            'loan_capital'] / 12
        portfolio_cash_flows['loan_nii'] = portfolio_cash_flows['noi'] - portfolio_cash_flows['loan_capital']
        portfolio_cash_flows['encumbered_loan_nii'] = portfolio_cash_flows['loan_nii'] * portfolio_cash_flows['encumbered']
        portfolio_cash_flows['unencumbered_loan_nii'] = portfolio_cash_flows['loan_nii'] * portfolio_cash_flows['encumbered'].apply(lambda x: x==False)
        portfolio_cash_flows['unsecured_interest_payment'] = portfolio_cash_flows['interest_payment'] * portfolio_cash_flows['Property Type'].apply(lambda x: x=='Fund-Level')
        portfolio_cash_flows['unsecured_debt_balance'] = portfolio_cash_flows['ending_balance'] * \
                                                             portfolio_cash_flows['Property Type'].apply(
                                                                 lambda x: x == 'Fund-Level')

        columns_order = [
            'date',
            'Property Name',
            'Property Type',
            'ownership_share',
            'acquisition_cost',
            'disposition_price',
            'partner_buyout_cost',
            'partial_sale_proceeds',
            'noi',
            'capex',
            'beginning_balance',
            'loan_draw',
            'interest_payment',
            'scheduled_principal_payment',
            'loan_paydown',
            'ending_balance',
            'market_value',
            'encumbered',
            'loan_capital',
            'loan_nii',
            'encumbered_loan_nii',
            'unencumbered_loan_nii',
            'unsecured_interest_payment',
            'unsecured_debt_balance'
        ]
        portfolio_cash_flows = portfolio_cash_flows[columns_order]
        return portfolio_cash_flows

    def combine_portfolio_cash_flows_df(self):
        property_cash_flows = pd.concat([
            property.combine_loan_cash_flows_df()
            for property in list(self.properties.values()
                                 )])
        property_cash_flows['date'] = pd.to_datetime(property_cash_flows['date']).dt.date

        unsecured_loan_cash_flows = self.combine_loan_schedules_df()
        unsecured_loan_cash_flows = unsecured_loan_cash_flows.loc[(unsecured_loan_cash_flows.date >= self.analysis_start_date) & (unsecured_loan_cash_flows.date <= self.analysis_end_date)]
        property_cash_flows['date'] = pd.to_datetime(property_cash_flows['date']).dt.date
        unsecured_loan_cash_flows['date'] = pd.to_datetime(unsecured_loan_cash_flows['date']).dt.date
        portfolio_cash_flows = pd.concat([property_cash_flows,unsecured_loan_cash_flows],axis=0)
        portfolio_cash_flows.fillna(0, inplace=True)
        portfolio_cash_flows = portfolio_cash_flows.drop(columns=['Property Name', 'Property Type'])
        portfolio_cash_flows = portfolio_cash_flows.groupby("date").sum().reset_index()

        return portfolio_cash_flows

    def get_portfolio_cash_flows_share_df(self):
        portfolio_cash_flows = self.concat_property_cash_flows_at_share_with_unsecured_loans()

        portfolio_cash_flows = portfolio_cash_flows.groupby("date").sum().reset_index()

        portfolio_cash_flows['capital_calls'] = portfolio_cash_flows['date'].map(self.capital_calls).fillna(0)
        portfolio_cash_flows['redemptions'] = portfolio_cash_flows['date'].map(self.redemptions).fillna(0)
        portfolio_cash_flows['distributions'] = portfolio_cash_flows['date'].map(self.distributions).fillna(0)

        portfolio_cash_flows['Net Cash Flow'] = (
            portfolio_cash_flows['noi'] -
            portfolio_cash_flows['capex'] -
            portfolio_cash_flows['acquisition_cost'] +
            portfolio_cash_flows['disposition_price'] -
            portfolio_cash_flows['partner_buyout_cost'] +
            portfolio_cash_flows['partial_sale_proceeds'] +
            portfolio_cash_flows['loan_draw'] -
            portfolio_cash_flows['loan_paydown'] -
            portfolio_cash_flows['interest_payment'] -
            portfolio_cash_flows['scheduled_principal_payment'] +
            portfolio_cash_flows['capital_calls'] -
            portfolio_cash_flows['redemptions'] -
            portfolio_cash_flows['distributions']

    )

        portfolio_cash_flows['beginning_cash'] = 0.0
        portfolio_cash_flows['ending_cash'] = 0.0

        # Set the first row's beginning cash to self.beginning_cash
        portfolio_cash_flows.iloc[0, portfolio_cash_flows.columns.get_loc('beginning_cash')] = self.beginning_cash

        # Calculate ending cash for the first row
        portfolio_cash_flows.iloc[0, portfolio_cash_flows.columns.get_loc('ending_cash')] = (
                portfolio_cash_flows.iloc[0, portfolio_cash_flows.columns.get_loc('beginning_cash')]
                + portfolio_cash_flows.iloc[0, portfolio_cash_flows.columns.get_loc('Net Cash Flow')]
        )

        # For subsequent rows, beginning_cash is the previous row's ending_cash
        for i in range(1, len(portfolio_cash_flows)):
            portfolio_cash_flows.iloc[i, portfolio_cash_flows.columns.get_loc('beginning_cash')] = \
            portfolio_cash_flows.iloc[i - 1, portfolio_cash_flows.columns.get_loc('ending_cash')]
            portfolio_cash_flows.iloc[i, portfolio_cash_flows.columns.get_loc('ending_cash')] = (
                    portfolio_cash_flows.iloc[i, portfolio_cash_flows.columns.get_loc('beginning_cash')]
                    + portfolio_cash_flows.iloc[i, portfolio_cash_flows.columns.get_loc('Net Cash Flow')]
            )

        portfolio_cash_flows.drop(columns=['Property Type','Property Name','ownership_share'],inplace=True)

        return portfolio_cash_flows





