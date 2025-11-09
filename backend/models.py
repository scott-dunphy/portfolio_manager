from database import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
import json

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
    auto_refinance_enabled = db.Column(db.Boolean, default=False)
    auto_refinance_spreads = db.Column(db.Text)
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
            'auto_refinance_enabled': bool(self.auto_refinance_enabled),
            'auto_refinance_spreads': self.get_auto_refinance_spreads(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'property_count': len(self.properties),
            'loan_count': len(self.loans)
        }

    def get_auto_refinance_spreads(self) -> dict:
        if not self.auto_refinance_spreads:
            return {}
        try:
            data = json.loads(self.auto_refinance_spreads)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, TypeError):
            pass
        return {}


class Property(db.Model):
    __tablename__ = 'properties'
    __table_args__ = (
        db.UniqueConstraint('portfolio_id', 'property_id', name='uq_properties_portfolio_property_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False)
    property_id = db.Column(db.String(100), nullable=False)
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
    market_value_start = db.Column(db.Float)

    # NOI and valuation
    noi_growth_rate = db.Column(db.Float)
    initial_noi = db.Column(db.Float)
    valuation_method = db.Column(db.String(50), default='growth')
    ownership_percent = db.Column(db.Float, default=1.0)
    capex_percent_of_noi = db.Column(db.Float, default=0.0)
    use_manual_noi_capex = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Additional fields can be stored as JSON
    additional_data = db.Column(db.Text)
    ownership_events = db.relationship(
        'PropertyOwnershipEvent',
        backref='property',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='PropertyOwnershipEvent.event_date'
    )
    manual_cash_flows = db.relationship(
        'PropertyManualCashFlow',
        backref='property',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='PropertyManualCashFlow.year'
    )

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
            'market_value_start': self.market_value_start,
            'noi_growth_rate': self.noi_growth_rate,
            'initial_noi': self.initial_noi,
            'valuation_method': self.valuation_method,
            'ownership_percent': self.ownership_percent,
            'capex_percent_of_noi': self.capex_percent_of_noi,
            'use_manual_noi_capex': self.use_manual_noi_capex,
            'manual_cash_flows': [entry.to_dict() for entry in self.manual_cash_flows],
            'ownership_events': [event.to_dict() for event in self.ownership_events],
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
    rate_type = db.Column(db.String(20), default='fixed')
    sofr_spread = db.Column(db.Float, default=0.0)
    interest_day_count = db.Column(db.String(20), default='30/360')
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
            'rate_type': self.rate_type,
            'sofr_spread': self.sofr_spread,
            'interest_day_count': self.interest_day_count,
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


class PropertyOwnershipEvent(db.Model):
    __tablename__ = 'property_ownership_events'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    ownership_percent = db.Column(db.Float, nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'property_id': self.property_id,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'ownership_percent': self.ownership_percent,
            'note': self.note
        }


class PropertyManualCashFlow(db.Model):
    __tablename__ = 'property_manual_cash_flows'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer)
    annual_noi = db.Column(db.Float)
    annual_capex = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'property_id': self.property_id,
            'year': self.year,
            'month': self.month,
            'annual_noi': self.annual_noi,
            'annual_capex': self.annual_capex,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
