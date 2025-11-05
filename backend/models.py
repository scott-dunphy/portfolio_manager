from database import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON

class Portfolio(db.Model):
    __tablename__ = 'portfolios'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    analysis_start_date = db.Column(db.Date, nullable=False)
    analysis_end_date = db.Column(db.Date, nullable=False)
    initial_unfunded_equity = db.Column(db.Float, default=0.0)
    beginning_cash = db.Column(db.Float, default=0.0)
    fee = db.Column(db.Float, default=0.0)
    beginning_nav = db.Column(db.Float, default=0.0)
    valuation_method = db.Column(db.String(50), default='growth')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    properties = db.relationship('Property', backref='portfolio', lazy=True, cascade='all, delete-orphan')
    loans = db.relationship('Loan', backref='portfolio', lazy=True, cascade='all, delete-orphan')
    preferred_equities = db.relationship('PreferredEquity', backref='portfolio', lazy=True, cascade='all, delete-orphan')
    cash_flows = db.relationship('CashFlow', backref='portfolio', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'analysis_start_date': self.analysis_start_date.isoformat() if self.analysis_start_date else None,
            'analysis_end_date': self.analysis_end_date.isoformat() if self.analysis_end_date else None,
            'initial_unfunded_equity': self.initial_unfunded_equity,
            'beginning_cash': self.beginning_cash,
            'fee': self.fee,
            'beginning_nav': self.beginning_nav,
            'valuation_method': self.valuation_method,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'property_count': len(self.properties),
            'loan_count': len(self.loans)
        }


class Property(db.Model):
    __tablename__ = 'properties'

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    property_id = db.Column(db.String(100), unique=True, nullable=False)
    property_name = db.Column(db.String(255), nullable=False)
    property_type = db.Column(db.String(100))
    address = db.Column(db.String(500))
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))

    # Financial data
    purchase_price = db.Column(db.Float)
    purchase_date = db.Column(db.Date)
    exit_date = db.Column(db.Date)
    exit_cap_rate = db.Column(db.Float)
    year_1_cap_rate = db.Column(db.Float)
    building_size = db.Column(db.Float)

    # NOI and valuation
    noi_growth_rate = db.Column(db.Float)
    initial_noi = db.Column(db.Float)
    valuation_method = db.Column(db.String(50), default='growth')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Additional fields can be stored as JSON
    additional_data = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'property_id': self.property_id,
            'property_name': self.property_name,
            'property_type': self.property_type,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'purchase_price': self.purchase_price,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'exit_date': self.exit_date.isoformat() if self.exit_date else None,
            'exit_cap_rate': self.exit_cap_rate,
            'year_1_cap_rate': self.year_1_cap_rate,
            'building_size': self.building_size,
            'noi_growth_rate': self.noi_growth_rate,
            'initial_noi': self.initial_noi,
            'valuation_method': self.valuation_method,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Loan(db.Model):
    __tablename__ = 'loans'

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=True)

    loan_id = db.Column(db.String(100), unique=True, nullable=False)
    loan_name = db.Column(db.String(255), nullable=False)
    principal_amount = db.Column(db.Float, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    origination_date = db.Column(db.Date, nullable=False)
    maturity_date = db.Column(db.Date, nullable=False)
    payment_frequency = db.Column(db.String(50), default='monthly')
    loan_type = db.Column(db.String(100))

    # Additional loan details
    amortization_period_months = db.Column(db.Integer)
    io_period_months = db.Column(db.Integer, default=0)
    origination_fee = db.Column(db.Float, default=0.0)
    exit_fee = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'property_id': self.property_id,
            'loan_id': self.loan_id,
            'loan_name': self.loan_name,
            'principal_amount': self.principal_amount,
            'interest_rate': self.interest_rate,
            'origination_date': self.origination_date.isoformat() if self.origination_date else None,
            'maturity_date': self.maturity_date.isoformat() if self.maturity_date else None,
            'payment_frequency': self.payment_frequency,
            'loan_type': self.loan_type,
            'amortization_period_months': self.amortization_period_months,
            'io_period_months': self.io_period_months,
            'origination_fee': self.origination_fee,
            'exit_fee': self.exit_fee,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class PreferredEquity(db.Model):
    __tablename__ = 'preferred_equities'

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=True)

    pref_equity_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    initial_investment = db.Column(db.Float, nullable=False)
    preferred_return = db.Column(db.Float, nullable=False)
    investment_date = db.Column(db.Date, nullable=False)
    redemption_date = db.Column(db.Date)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'property_id': self.property_id,
            'pref_equity_id': self.pref_equity_id,
            'name': self.name,
            'initial_investment': self.initial_investment,
            'preferred_return': self.preferred_return,
            'investment_date': self.investment_date.isoformat() if self.investment_date else None,
            'redemption_date': self.redemption_date.isoformat() if self.redemption_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class CashFlow(db.Model):
    __tablename__ = 'cash_flows'

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'), nullable=True)

    date = db.Column(db.Date, nullable=False)
    cash_flow_type = db.Column(db.String(100), nullable=False)  # 'capital_call', 'distribution', 'redemption', etc.
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'property_id': self.property_id,
            'loan_id': self.loan_id,
            'date': self.date.isoformat() if self.date else None,
            'cash_flow_type': self.cash_flow_type,
            'amount': self.amount,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
