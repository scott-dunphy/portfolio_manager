from portfolio_manager.Property import Property
from portfolio_manager.Loan import Loan
from portfolio_manager.PreferredEquity import PreferredEquity
from portfolio_manager.CarriedInterest import CarriedInterest, TierParams
import pandas as pd
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from collections import OrderedDict
from typing import Optional
import pandas as pd
import logging
import requests
import numpy as np


class Portfolio:
    def __init__(self,
        analysis_start_date: date,
        analysis_end_date: date,
        initial_unfunded_equity: float = 0,
                 ):

        self.properties = {}  # Key: Property ID, Value: Property instance
        self.loans = {}
        self.unfunded_equity = {}
        self.preferred_equity = {}
        self.initial_unfunded_equity = initial_unfunded_equity
        self.analysis_start_date = analysis_start_date
        self.analysis_end_date = analysis_end_date
        self.beginning_cash = 0
        self.capital_calls = {}
        self.redemptions = {}
        self.drip = {}
        self.treasury_rates = {}
        self.distributions = {}
        self.month_list = self.get_month_list(self.analysis_start_date, self.analysis_end_date)
        #self.fetch_treasury_rates()
        self.fee = 0
        self.beginning_nav = 0
        self.valuation_method = "growth"



        self.loan_capital = {
            'Residential': 200,
            'Office': 0.15,
            'Retail': 0.20,
            'Industrial': 0.10,
                             }

    def set_file_path(self, file_path):
        self.file_path = file_path

    def set_fee(self, fee):
        self.fee = fee

    def set_beginning_nav(self, nav):
        self.beginning_nav = nav

    def get_loan_capital(self, building_size, property_type):
        return building_size * self.loan_capital.get(property_type, 0)

    def set_initial_unfunded_equity(self, initial_unfunded_equity):
        self.initial_unfunded_equity = initial_unfunded_equity

    def set_valuation_method(self, valuation_method):
        for prop in self.properties.values():
            prop.set_valuation_method(valuation_method=valuation_method)

    def get_month_list(self, start_date: date, end_date: date) -> list:
        if start_date > end_date:
            raise ValueError("start_date must be on or before end_date.")

        month_list = []
        current_date = self.ensure_date(start_date)

        while current_date <= end_date:
            month_list.append(current_date)
            # Move to the next month
            current_date = self.ensure_date(current_date + relativedelta(months=1))

        return month_list

    def calculate_unfunded_commitments(self):
        for i, month in enumerate(self.month_list):
            if i==0:
                self.unfunded_equity[month] = self.initial_unfunded_equity
            else:
                prior_month = self.month_list[i-1]
                unfunded = self.unfunded_equity[prior_month] - self.capital_calls.get(month,0)
                self.unfunded_equity[month] = unfunded
                if unfunded < 0:
                    logging.warning(f"{month}: Capital calls exceed available unfunded commitments -- Unfunded: ${unfunded:,.0f}.")
        return self.unfunded_equity

    def get_unfunded_commitments_df(self):
        unfunded = self.calculate_unfunded_commitments()
        df = pd.DataFrame(list(unfunded.items()), columns=['date','unfunded_commitment'])
        return df

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
            property.set_treasury_rates(self.treasury_rates)
        self.load_preferred_equity()
        self.calculate_unfunded_commitments()
        self.load_promotes()
        self.load_promote_cash_flows()



    def read_import_file(self, sheet_name, use_cols: Optional[list] = None):
        if use_cols is not None:
            df = pd.read_excel(self.file_path, sheet_name=sheet_name, dtype={'id': str, 'property_id': str,'property_id_':str}, usecols=use_cols)
        else:
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

    def load_preferred_equity(self, df: Optional[pd.DataFrame] = None):
        if df is None:
            df = self.read_import_file('Preferred Equity')
        df['id'] = df['id'].fillna('').astype(str)
        for i, row in df.iterrows():
            id = row['id']
            property_id = str(row['property_id'])
            loan_id = str(row['loan_id'])
            ownership_share = row['ownership_share']
            property = self.get_property(property_id)
            loan = property.get_loan(loan_id)
            preferred_equity = PreferredEquity(id, loan, ownership_share)
            self.add_preferred_equity(preferred_equity)

    def load_promotes(self, df: Optional[pd.DataFrame] = None):
        if df is None:
            df = self.read_import_file('Promotes', use_cols=['property_id', 'tier_number', 'hurdle_rate', 'lp_distribution'])
            df = df.sort_values(['property_id','tier_number'], ascending=[1,1])
            df = df.loc[~df.property_id.isna()]
        for i, row in df.iterrows():
            property_id = row['property_id']
            property = self.get_property(property_id)
            property.add_promote_tier(TierParams(hurdle_rate=row['hurdle_rate'], lp_dist_ratio=row['lp_distribution']))
    def load_promote_cash_flows(self, df: Optional[pd.DataFrame] = None):
        if df is None:
            # Read the data with specific columns
            df = self.read_import_file('Promotes', use_cols=['property_id_', 'date', 'cash_flow'])
            df['date'] = df['date'].apply(lambda x: self.ensure_date(x))
            #print(df.columns)
        # Ensure the DataFrame has the required columns
        required_columns = {'property_id_', 'date', 'cash_flow'}
        if not required_columns.issubset(df.columns):
            raise ValueError(f"The DataFrame must contain the following columns: {required_columns}")

        # Group by property_id to handle cash flows for each property separately
        grouped = df.groupby('property_id_')

        for property_id, group in grouped:
            # Retrieve the property object
            property_obj = self.properties.get(property_id)

            if property_obj is None:
                raise KeyError(f"Property with ID {property_id} not found in portfolio.")

            # Ensure the cash flows DataFrame for this property is sorted and properly formatted
            cash_flow_df = group[['date', 'cash_flow']].sort_values(by='date').reset_index(drop=True)

            # Add promote cash flows to the property
            property_obj.add_promote_cash_flows(cash_flow_df)

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
                    encumbered=row['encumbered'],
                    cap_rate=row['cap_rate'],
                    exit_cap_rate=row['exit_cap_rate'],
                    capex_percent_of_noi=row['capex_percent_of_noi'],
                    promote=row['promote'],
                    upper_tier_share = row['upper_tier_share'] if not pd.isna(row['upper_tier_share']) else None
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

        drip = dict(zip(
            df.loc[(df['cash_flow'] == 'drip'), 'date'].apply(self.ensure_date),
            df.loc[(df['cash_flow'] == 'drip'), 'amount']
        ))

        distributions = dict(zip(
            df.loc[(df['cash_flow'] == 'distribution'), 'date'].apply(self.ensure_date),
            df.loc[(df['cash_flow'] == 'distribution'), 'amount']
        ))
        self.capital_calls = capital_calls
        self.redemptions = redemptions
        self.distributions = distributions
        self.drip = drip


    def load_property_loans(self, df: Optional[pd.DataFrame] = None):
        if df is None:
            df = self.read_import_file('Secured Loans')
        #df = pd.read_excel(self.file_path, sheet_name="Secured Loans", dtype={'id': str, 'property_id': str})

        # Ensure IDs are strings and handle missing values
        df['id'] = df['id'].fillna('').astype(str)
        df['property_id'] = df['property_id'].fillna('').astype(str)

        for _, row in df.iterrows():
            # Create Loan instance
            #print(row['id'])
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
                foreclosure_date=row['foreclosure_date'],
                market_rate=row['market_rate'],
                fixed_floating=row['fixed_floating'],
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
                foreclosure_date=row['foreclosure_date'],
                market_rate=row['market_rate'],
                fixed_floating=row['fixed_floating'],
            )

            self.add_loan(loan)

    def load_unsecured_loan_flows(self, df: Optional[pd.DataFrame] = None):
        if df is None:
            df = self.read_import_file('Unsecured Loan Flows')
        df['id'] = df['id'].fillna('').astype(str)

        # Sort flows by date to ensure sequential processing
        df = df.sort_values(by=['date', 'id', 'flow_type'])

        for _, row in df.iterrows():
            loan_id = row['id']
            flow_type = row['flow_type']
            date_ = self.ensure_date(row['date'])
            amount = row['amount']

            # Sequentially apply draws and paydowns
            if flow_type == 'draw':
                self.add_loan_draw(loan_id, amount, date_)
            elif flow_type == 'paydown':
                self.add_loan_paydown(loan_id, amount, date_)
            else:
                raise ValueError(f"Invalid flow type: {flow_type}")

    def add_property(self, property):
        self.properties[property.id] = property

    def add_preferred_equity(self, preferred_equity):
        self.preferred_equity[preferred_equity.id] = preferred_equity

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

    def set_beginning_cash(self, cash):
        self.beginning_cash = cash

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

    def concat_preferred_equity_schedules_df(self):
        if not self.preferred_equity:  # No preferred equity
            logging.info("No preferred equity to process.")
            return pd.DataFrame(columns=['date', 'preferred_equity_id', 'encumbered'])  # Adjust columns as needed

        preferred_equities = []
        for preferred_equity in self.preferred_equity.values():
            df = preferred_equity.generate_preferred_equity_schedule_df()
            df['preferred_equity_id'] = preferred_equity.id
            cols = df.columns[-1:].append(df.columns[:-1])
            preferred_equities.append(df[cols])

        return pd.concat(preferred_equities)

    def concat_preferred_equity_schedules_share_df(self):
        if not self.preferred_equity:  # No preferred equity
            logging.info("No preferred equity to process.")
            return pd.DataFrame(
                columns=['date', 'preferred_equity_id', 'ownership_share', 'encumbered'])  # Adjust columns

        preferred_equities = []
        for preferred_equity in self.preferred_equity.values():
            df = preferred_equity.get_preferred_equity_schedule_share_df_by_date(self.analysis_start_date, self.analysis_end_date)
            df['preferred_equity_id'] = preferred_equity.id
            cols = df.columns[-1:].append(df.columns[:-1])
            preferred_equities.append(df[cols])

        return pd.concat(preferred_equities)


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

    def concat_property_loan_cash_flows_at_share(self):
        schedules = []
        for property in list(self.properties.values()):
            if len(property.loans) > 0:
                property_loan_cash_flows = property.concat_loan_schedules_at_share_df()
                property_loan_cash_flows['Property Name'] = property.name
                property_loan_cash_flows['Property Type'] = property.property_type
                schedules.append(property_loan_cash_flows)
        df = pd.concat(schedules)
        df = df.fillna(0)
        return df

    def concat_property_loan_cash_flows_at_share_with_unsecured_loans(self):
        property_cash_flows = self.concat_property_loan_cash_flows_at_share()
        unsecured_loan_cash_flows = self.concat_loan_schedules_df()
        unsecured_loan_cash_flows['date'] = pd.to_datetime(unsecured_loan_cash_flows['date']).dt.date
        unsecured_loan_cash_flows.rename(columns={'loan_id': 'Property Name'}, inplace=True)
        unsecured_loan_cash_flows['Property Type'] = 'Fund-Level'
        portfolio_cash_flows = pd.concat([property_cash_flows, unsecured_loan_cash_flows], axis=0)
        return portfolio_cash_flows

    def concat_property_cash_flows_at_share_with_unsecured_loans(self):
        property_cash_flows = self.concat_property_cash_flows_at_share()
        unsecured_loan_cash_flows = self.concat_loan_schedules_df()
        unsecured_loan_cash_flows = unsecured_loan_cash_flows.loc[(unsecured_loan_cash_flows.date >= self.analysis_start_date) & (unsecured_loan_cash_flows.date <= self.analysis_end_date)]
        unsecured_loan_cash_flows['date'] = pd.to_datetime(unsecured_loan_cash_flows['date']).dt.date
        unsecured_loan_cash_flows.rename(columns={'loan_id':'Property Name'},inplace=True)
        unsecured_loan_cash_flows['Property Type'] = 'Fund-Level'

        portfolio_cash_flows = pd.concat([property_cash_flows, unsecured_loan_cash_flows], axis=0)
        # Handle preferred equity cash flows
        if not self.preferred_equity:
            preferred_equity_cash_flows = pd.DataFrame({
                'date': pd.Series(dtype='object'),
                'preferred_equity_draw': pd.Series(dtype='float'),
                'preferred_equity_repayment': pd.Series(dtype='float')
            })
        else:
            preferred_equity_cash_flows = self.concat_preferred_equity_schedules_share_df()
        portfolio_cash_flows = pd.concat([portfolio_cash_flows, preferred_equity_cash_flows], axis=0)
        portfolio_cash_flows.fillna(value=0, inplace=True)

        loan_capital = self.get_loan_capital_df().drop_duplicates(subset=['Property Name'])
        portfolio_cash_flows = portfolio_cash_flows.merge(loan_capital, how='left', on='Property Name')
        portfolio_cash_flows.fillna(value=0, inplace=True)
        portfolio_cash_flows['loan_capital'] = portfolio_cash_flows['ownership_share'] * portfolio_cash_flows[
            'loan_capital'] / 12
        portfolio_cash_flows['loan_nii'] = portfolio_cash_flows['noi'] - portfolio_cash_flows['loan_capital']
        portfolio_cash_flows['encumbered_loan_nii'] = portfolio_cash_flows['loan_nii'] * portfolio_cash_flows['encumbered']
        portfolio_cash_flows['unencumbered_loan_nii'] = portfolio_cash_flows['loan_nii'] * portfolio_cash_flows['encumbered'].apply(lambda x: x==False)
        portfolio_cash_flows['encumbered_market_value'] = portfolio_cash_flows['market_value'] * portfolio_cash_flows['encumbered'].apply(lambda x: x == True)
        portfolio_cash_flows['unencumbered_market_value'] = portfolio_cash_flows['market_value'] * portfolio_cash_flows['encumbered'].apply(lambda x: x == False)
        portfolio_cash_flows['unsecured_interest_payment'] = portfolio_cash_flows['interest_payment'] * portfolio_cash_flows['Property Type'].apply(lambda x: x=='Fund-Level')
        portfolio_cash_flows['secured_interest_payment'] = portfolio_cash_flows['interest_payment'] - portfolio_cash_flows['unsecured_interest_payment']
        portfolio_cash_flows['unsecured_debt_balance'] = portfolio_cash_flows['ending_balance'] * \
                                                             portfolio_cash_flows['Property Type'].apply(
                                                                 lambda x: x == 'Fund-Level')
        portfolio_cash_flows['secured_debt_balance'] = portfolio_cash_flows['ending_balance'] - portfolio_cash_flows['unsecured_debt_balance']

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
            'preferred_equity_draw',
            'preferred_equity_repayment',
            'beginning_balance',
            'loan_draw',
            'interest_payment',
            'scheduled_principal_payment',
            'loan_paydown',
            'ending_balance',
            'foreclosure_market_value',
            'market_value',
            'encumbered',
            'loan_capital',
            'loan_nii',
            'encumbered_loan_nii',
            'unencumbered_loan_nii',
            'encumbered_market_value',
            'unencumbered_market_value',
            'unsecured_interest_payment',
            'secured_interest_payment',
            'unsecured_debt_balance',
            'secured_debt_balance',
            'gross_income',
            'gain_loss',
            'gain_loss_dilution',
            'gross_income_loss_dilution',
            'effective_share',
            'nav_dilution',

        ]
        portfolio_cash_flows = portfolio_cash_flows[columns_order]
        portfolio_cash_flows = portfolio_cash_flows.loc[ (portfolio_cash_flows.date >= self.analysis_start_date) & (portfolio_cash_flows.date <= self.analysis_end_date)]
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
        portfolio_cash_flows.fillna(value=0, inplace=True)


        return portfolio_cash_flows

    def get_portfolio_cash_flows_share_df(self):
        portfolio_cash_flows = self.concat_property_cash_flows_at_share_with_unsecured_loans()

        # Group by date and sum cash flows
        portfolio_cash_flows = portfolio_cash_flows.groupby("date").sum().reset_index()

        # Map capital calls, redemptions, and distributions
        portfolio_cash_flows['capital_calls'] = portfolio_cash_flows['date'].map(self.capital_calls).fillna(0)
        portfolio_cash_flows['drip'] = portfolio_cash_flows['date'].map(self.drip).fillna(0)
        portfolio_cash_flows['redemptions'] = portfolio_cash_flows['date'].map(self.redemptions).fillna(0)
        portfolio_cash_flows['distributions'] = portfolio_cash_flows['date'].map(self.distributions).fillna(0)

        # Calculate net cash flow
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
                portfolio_cash_flows['capital_calls'] +
                portfolio_cash_flows['drip'] -
                portfolio_cash_flows['redemptions'] -
                portfolio_cash_flows['distributions'] -
                portfolio_cash_flows['preferred_equity_draw'] +
                portfolio_cash_flows['preferred_equity_repayment']
        )

        # Initialize beginning and ending cash columns
        portfolio_cash_flows['beginning_cash'] = 0.0
        portfolio_cash_flows['ending_cash'] = 0.0

        # Determine the starting index for analysis_start_date
        if self.analysis_start_date in portfolio_cash_flows['date'].values:
            start_index = portfolio_cash_flows.index[portfolio_cash_flows['date'] == self.analysis_start_date][0]
        else:
            start_index = 0

        # Set beginning and ending cash for the first period based on set_beginning_cash
        initial_cash = self.beginning_cash if self.beginning_cash is not None else 0.0
        portfolio_cash_flows.at[start_index, 'beginning_cash'] = initial_cash
        portfolio_cash_flows.at[
            start_index, 'ending_cash'] = initial_cash  # Ensure first month's ending cash equals beginning cash

        # Process each period, deducting management fee as needed
        for i in range(start_index+1, len(portfolio_cash_flows)):
            # For subsequent periods, carry over ending cash from previous period
            if i > start_index:
                portfolio_cash_flows.at[i, 'beginning_cash'] = portfolio_cash_flows.at[i - 1, 'ending_cash']

            # Calculate provisional ending cash for this period before fee deduction
            provisional_ending_cash = portfolio_cash_flows.at[i, 'beginning_cash'] + portfolio_cash_flows.at[
                i, 'Net Cash Flow']

            # Temporarily assign provisional ending cash
            portfolio_cash_flows.at[i, 'ending_cash'] = provisional_ending_cash

            # Calculate net asset value before fee deduction for this period
            nav_before_fee = (
                    portfolio_cash_flows.at[i, 'market_value'] -
                    portfolio_cash_flows.at[i, 'ending_balance'] +
                    provisional_ending_cash
            )

            # If it's the start of a quarter, calculate and deduct management fee
            current_date = pd.to_datetime(portfolio_cash_flows.at[i, 'date'])
            if current_date.month % 3 == 1:  # Assuming quarter start months (Jan, Apr, Jul, Oct)
                management_fee = nav_before_fee * self.fee / 4
            else:
                management_fee = 0

            # Deduct the fee from the provisional ending cash
            adjusted_ending_cash = provisional_ending_cash - management_fee

            # Update the DataFrame with the fee and adjusted cash
            portfolio_cash_flows.at[i, 'management_fee'] = management_fee
            portfolio_cash_flows.at[i, 'ending_cash'] = adjusted_ending_cash

            # Recalculate net asset value after fee deduction for record-keeping
            portfolio_cash_flows.at[i, 'net_asset_value'] = (
                    portfolio_cash_flows.at[i, 'market_value'] -
                    portfolio_cash_flows.at[i, 'ending_balance'] +
                    adjusted_ending_cash
            )

            # Check for negative cash and log a warning
            if adjusted_ending_cash < 0:
                logging.warning(
                    f"Warning: Cash is negative in period {i + 1}: ${adjusted_ending_cash:,.0f}. Consider a revolver draw or capital call."
                )

        # After loop operations for remaining calculations:

        # Add unfunded commitments
        portfolio_cash_flows = portfolio_cash_flows.merge(
            self.get_unfunded_commitments_df(), how='left', on='date'
        )
        portfolio_cash_flows.drop(['Property Name', 'Property Type', 'ownership_share'], axis=1, inplace=True)
        portfolio_cash_flows = portfolio_cash_flows.loc[
            (portfolio_cash_flows.date >= self.analysis_start_date) &
            (portfolio_cash_flows.date <= self.analysis_end_date)
            ]

        portfolio_cash_flows['leverage_ratio'] = (
                portfolio_cash_flows.ending_balance /
                (portfolio_cash_flows.market_value + portfolio_cash_flows.ending_cash)
        )
        portfolio_cash_flows['unencumbered_leverage_ratio'] = (
                portfolio_cash_flows.unsecured_debt_balance /
                portfolio_cash_flows.unencumbered_market_value
        )
        portfolio_cash_flows['encumbered_leverage_ratio'] = (
                portfolio_cash_flows.secured_debt_balance /
                portfolio_cash_flows.encumbered_market_value
        )

        portfolio_cash_flows['gross_income'] = portfolio_cash_flows['noi'] - portfolio_cash_flows['interest_payment']
        # portfolio_cash_flows['gain_loss'] = portfolio_cash_flows['market_value'] - portfolio_cash_flows['capex']

        # Set first period values to zero except for NetAssetValue and MarketValue
        keep_cols = ['net_asset_value', 'ending_cash', 'market_value']
        zero_cols = portfolio_cash_flows.columns.difference(keep_cols)
        # Ensure the very first row (index 0 of analysis period) has the correct initial NAV
        first_row_index = portfolio_cash_flows.index[0]
        portfolio_cash_flows.loc[first_row_index, zero_cols] = 0
        portfolio_cash_flows.at[first_row_index, 'net_asset_value'] = self.beginning_nav

        portfolio_cash_flows = self.calculate_income_and_gains(portfolio_cash_flows)
        return portfolio_cash_flows

    def concat_property_loans(self):
        loan_schedules = []
        for property in self.properties.values():
            if hasattr(property,
                       'loans') and property.loans:  # Check if property has loans attribute and it's not empty
                for loan in property.loans.values():
                    loan_schedule = loan.generate_loan_schedule_df()
                    loan_schedule['loan_id'] = loan.id
                    loan_schedules.append(loan_schedule)

        if not loan_schedules:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=['date', 'beginning_balance', 'loan_draw',
                                         'loan_paydown', 'interest_payment',
                                         'scheduled_principal_payment', 'ending_balance'])

        df = pd.concat(loan_schedules)
        return df

    def value_property_loans(self, as_of_date, discount_rate_spread):
        loan_schedules = []
        as_of_date = self.ensure_date(as_of_date)
        for property in self.properties.values():
            if property.loans:  # Check if property has loans attribute and it's not empty
                for loan in property.loans.values():
                    loan_schedule = loan.generate_loan_schedule_df()
                    max_date = loan_schedule['date'].max()
                    if max_date <= as_of_date:
                        logging.warning(f"{loan.id}: Loan cash flows end before as of date.")
                        continue
                    current_balance = loan_schedule.loc[loan_schedule.date == as_of_date, 'ending_balance'].iloc[0]
                    rate = loan.market_rate + discount_rate_spread
                    loan_value = loan.calculate_loan_market_value(as_of_date, rate)
                    loan_df = pd.DataFrame([[loan.id, as_of_date, current_balance, rate, loan_value]], columns=['Loan Id','As of Date','Current Balance','Market Rate','Loan Value'])
                    loan_schedules.append(loan_df)
        df = pd.concat(loan_schedules)
        return df

    def value_property_loans_with_valuer(self, as_of_date):
        loan_schedules = []
        as_of_date = self.ensure_date(as_of_date)
        for property in self.properties.values():
            if property.loans:  # Check if property has loans attribute and it's not empty
                for loan in property.loans.values():
                    loan_schedule = loan.generate_loan_schedule_df()
                    max_date = loan_schedule['date'].max()
                    if max_date <= as_of_date:
                        logging.warning(f"{loan.id}: Loan cash flows end before as of date.")
                        continue
                    rate = loan.rate
                    market_value, market_rate = loan.value_loan(as_of_date, treasury_rates=self.treasury_rates)
                    current_balance = loan_schedule.loc[loan_schedule.date == as_of_date, 'ending_balance'].iloc[0]
                    spread = loan.spread
                    loan_df = pd.DataFrame([[loan.id, as_of_date, current_balance, rate, market_rate, spread, market_value]], columns=['Loan Id','As of Date','Current Balance','Note Rate', 'Market Rate', 'Spead', 'Loan Value'])
                    loan_schedules.append(loan_df)
        for loan in self.loans.values():
            loan_schedule = loan.generate_loan_schedule_df()
            max_date = loan_schedule['date'].max()
            if max_date <= as_of_date:
                logging.warning(f"{loan.id}: Loan cash flows end before as of date.")
                continue
            rate = loan.rate
            market_value, market_rate = loan.value_loan(as_of_date, treasury_rates=self.treasury_rates)
            current_balance = loan_schedule.loc[loan_schedule.date == as_of_date, 'ending_balance'].iloc[0]
            spread = loan.spread
            loan_df = pd.DataFrame(
                [[loan.id, as_of_date, current_balance, rate, market_rate, spread, market_value]],
                columns=['Loan Id', 'As of Date', 'Current Balance', 'Note Rate', 'Market Rate', 'Spead',
                         'Loan Value'])
            loan_schedules.append(loan_df)
        df = pd.concat(loan_schedules)
        return df

    def value_property_loans_at_share_with_valuer(self, as_of_date, chatham_style=True):
        loan_schedules = []
        columns = ['Loan Id', 'As of Date', 'Note Rate', 'Market Rate', 'Spread',
                   'Ownership Share', 'Current Balance', 'Loan Value']
        as_of_date = self.ensure_date(as_of_date)
        for property in self.properties.values():
            if property.loans:  # Check if property has loans attribute and it's not empty
                for loan in property.loans.values():
                    loan_schedule = loan.generate_loan_schedule_df()
                    max_date = loan_schedule['date'].max()
                    if max_date <= as_of_date:
                        logging.warning(f"{loan.id}: Loan cash flows end before as of date.")
                        continue
                    rate = loan.rate
                    market_value, market_rate = loan.value_loan(as_of_date, treasury_rates=self.treasury_rates, chatham_style=chatham_style)
                    current_balance = loan_schedule.loc[loan_schedule.date == as_of_date, 'ending_balance'].iloc[0]
                    spread = loan.spread or None
                    ownership_share = self.properties.get(loan.property_id).get_ownership_share(as_of_date)
                    loan_df = pd.DataFrame([[loan.id, as_of_date, rate, market_rate, spread, ownership_share, current_balance*ownership_share, market_value*ownership_share]], columns=columns)
                    loan_schedules.append(loan_df)
        for loan in self.loans.values():
            loan_schedule = loan.generate_loan_schedule_df()
            max_date = loan_schedule['date'].max()
            if max_date <= as_of_date:
                logging.warning(f"{loan.id}: Loan cash flows end before as of date.")
                continue
            rate = loan.rate
            market_value, market_rate = loan.value_loan(as_of_date, treasury_rates=self.treasury_rates, chatham_style=chatham_style)
            current_balance = loan_schedule.loc[loan_schedule.date == as_of_date, 'ending_balance'].iloc[0]
            spread = loan.spread
            loan_df = pd.DataFrame(
                [[loan.id, as_of_date, rate, market_rate, spread, 1, current_balance, market_value]],
                columns=columns)
            loan_schedules.append(loan_df)
        df = pd.concat(loan_schedules)
        return df

    def calculate_income_and_gains(self, df):
        df['market_value_change'] = df['market_value'].diff()
        df['gain_loss'] = df['market_value_change'] - df['capex'] - df['partner_buyout_cost'] + df['disposition_price'] - df['acquisition_cost'] + df['preferred_equity_repayment'] - df['preferred_equity_draw'] + df['partial_sale_proceeds'] + df['foreclosure_market_value']
        df['beginning_nav'] = df['net_asset_value'].shift(3)
        cols_to_sum = ['capital_calls', 'drip']
        df['capital_activity'] = df.apply(
            lambda row: (
                    df.loc[row.name - 2:row.name, cols_to_sum].sum().sum() -
                    df.loc[row.name - 2:row.name, 'redemptions'].sum()
            ), axis=1
        )
        df['denominator'] = df['beginning_nav'] + df['capital_activity']
        df['t3_income'] = df.apply(lambda row: (df.loc[row.name - 2:row.name, 'gross_income'].sum()), axis=1)
        df['t3_gain_loss'] = df.apply(lambda row: (df.loc[row.name - 2:row.name, 'gain_loss'].sum()), axis=1)
        df['income_return'] = df['t3_income'] / df['denominator']
        df['appreciation_return'] = df['t3_gain_loss'] / df['denominator']
        df['total_return'] = df['income_return'] + df['appreciation_return']
        drop_cols = ['beginning_nav', 'capital_activity','t3_income', 't3_gain_loss']
        df.drop(columns=drop_cols,inplace=True)
        return df

    def calculate_change_in_loan_values(self, current_period, prior_period):
        current_period = self.ensure_date(current_period)
        prior_period = self.ensure_date(prior_period)
        current_df = self.value_property_loans_at_share_with_valuer(current_period)
        prior_df = self.value_property_loans_at_share_with_valuer(prior_period)
        current_df = current_df.merge(prior_df, on='Loan Id', how='left')
        return current_df

    from datetime import date

    def fetch_treasury_rates(self, series_id: str = 'DGS10'):
        # Fetch rates from FRED API
        fred_base_url = "https://api.stlouisfed.org/fred/series/observations"
        start_date = date(2013, 1, 1)  # Fixed start date
        end_date = date.today()  # Use the current date as the end date

        fred_params = {
            "series_id": series_id,
            "api_key": "b73eb39061969ce96b4a673f93d0898e",
            "file_type": "json",
            "observation_start": start_date.strftime("%Y-%m-%d"),
            "observation_end": end_date.strftime("%Y-%m-%d"),
        }

        fred_response = requests.get(fred_base_url, params=fred_params)

        if fred_response.status_code == 200:
            fred_data = fred_response.json()
            observations = fred_data.get("observations", [])
            for obs in observations:
                obs_date = date.fromisoformat(obs["date"])
                try:
                    self.treasury_rates[obs_date] = float(obs["value"]) / 100  # Convert percentage to decimal
                except ValueError:
                    continue  # Skip invalid data
        else:
            raise ValueError(f"FRED API request failed: {fred_response.status_code}, {fred_response.text}")

        # Fetch rates from Chatham Financial API
        chatham_url = "https://www.chathamfinancial.com/getrates/278177"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        }
        chatham_response = requests.get(chatham_url, headers=headers)

        if chatham_response.status_code == 200:
            chatham_data = chatham_response.json()
            for rate_entry in chatham_data.get("Rates", []):
                try:
                    raw_date = date.fromisoformat(rate_entry["Date"][:10])  # Extract only the date part
                    eom_date = self.ensure_date(raw_date)  # Convert to end-of-month using ensure_date
                    rate_value = rate_entry["Rate"]
                    self.treasury_rates[eom_date] = rate_value  # Add directly in decimal format
                except (ValueError, KeyError):
                    continue  # Skip invalid data
        else:
            raise ValueError(f"Chatham API request failed: {chatham_response.status_code}, {chatham_response.text}")




