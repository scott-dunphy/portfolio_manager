from flask import Blueprint, request, jsonify, current_app
from database import db
from models import Loan
from datetime import datetime
from services.cash_flow_service import clear_loan_cash_flows, regenerate_loan_cash_flows

ALLOWED_DAY_COUNTS = {'30/360', 'actual/360', 'actual/365'}


def _normalize_day_count(value):
    normalized = (value or '30/360').lower().replace('_', '/')
    if normalized not in ALLOWED_DAY_COUNTS:
        return None
    return normalized

bp = Blueprint('loans', __name__, url_prefix='/api/loans')

@bp.route('', methods=['GET'])
def get_loans():
    """Get all loans, optionally filtered by portfolio_id"""
    portfolio_id = request.args.get('portfolio_id', type=int)

    if portfolio_id:
        loans = Loan.query.filter_by(portfolio_id=portfolio_id).all()
    else:
        loans = Loan.query.all()

    return jsonify([l.to_dict() for l in loans])

@bp.route('/<int:loan_id>', methods=['GET'])
def get_loan(loan_id):
    """Get a specific loan"""
    loan = Loan.query.get_or_404(loan_id)
    return jsonify(loan.to_dict())

@bp.route('', methods=['POST'])
def create_loan():
    """Create a new loan"""
    data = request.get_json()

    try:
        rate_type = (data.get('rate_type') or 'fixed').lower()
        if rate_type not in ('fixed', 'floating'):
            return jsonify({"error": "rate_type must be 'fixed' or 'floating'"}), 400
        day_count = _normalize_day_count(data.get('interest_day_count'))
        if day_count is None:
            return jsonify({"error": "interest_day_count must be one of 30/360, Actual/360, Actual/365"}), 400

        interest_rate = data.get('interest_rate')
        if rate_type == 'fixed':
            if interest_rate is None:
                return jsonify({"error": "interest_rate is required for fixed-rate loans"}), 400
        else:
            interest_rate = interest_rate or 0.0

        property_id = data.get('property_id')
        if isinstance(property_id, str) and property_id.strip() == '':
            property_id = None
        elif property_id is not None and not isinstance(property_id, int):
            property_id = int(property_id)

        loan = Loan(
            portfolio_id=data['portfolio_id'],
            property_id=property_id,
            loan_id=data['loan_id'],
            loan_name=data['loan_name'],
            principal_amount=data['principal_amount'],
            interest_rate=interest_rate,
            rate_type=rate_type,
            interest_day_count=day_count,
            sofr_spread=data.get('sofr_spread', 0.0),
            origination_date=datetime.fromisoformat(data['origination_date']).date(),
            maturity_date=datetime.fromisoformat(data['maturity_date']).date(),
            payment_frequency=data.get('payment_frequency', 'monthly'),
            loan_type=data.get('loan_type'),
            amortization_period_months=data.get('amortization_period_months'),
            io_period_months=data.get('io_period_months', 0),
            origination_fee=data.get('origination_fee', 0.0),
            exit_fee=data.get('exit_fee', 0.0)
        )

        db.session.add(loan)
        db.session.commit()

        try:
            regenerate_loan_cash_flows(loan)
        except Exception:
            current_app.logger.exception('Failed to regenerate cash flows for loan %s', loan.id)

        return jsonify(loan.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@bp.route('/<int:loan_id>', methods=['PUT'])
def update_loan(loan_id):
    """Update an existing loan"""
    loan = Loan.query.get_or_404(loan_id)
    data = request.get_json()

    try:
        if 'rate_type' in data:
            rate_type = (data['rate_type'] or 'fixed').lower()
            if rate_type not in ('fixed', 'floating'):
                return jsonify({"error": "rate_type must be 'fixed' or 'floating'"}), 400
            loan.rate_type = rate_type
            if rate_type == 'floating' and (loan.interest_rate is None or loan.interest_rate == 0):
                loan.interest_rate = 0.0
        if 'interest_day_count' in data:
            day_count = _normalize_day_count(data.get('interest_day_count'))
            if day_count is None:
                return jsonify({"error": "interest_day_count must be one of 30/360, Actual/360, Actual/365"}), 400
            loan.interest_day_count = day_count

        # Update fields if provided
        for field in ['loan_name', 'principal_amount', 'interest_rate', 'payment_frequency',
                      'loan_type', 'amortization_period_months', 'io_period_months',
                      'origination_fee', 'exit_fee', 'sofr_spread']:
            if field in data:
                setattr(loan, field, data[field])
        if 'property_id' in data:
            property_id = data.get('property_id')
            if isinstance(property_id, str) and property_id.strip() == '':
                property_id = None
            elif property_id is not None and not isinstance(property_id, int):
                property_id = int(property_id)
            loan.property_id = property_id

        if 'origination_date' in data:
            loan.origination_date = datetime.fromisoformat(data['origination_date']).date()
        if 'maturity_date' in data:
            loan.maturity_date = datetime.fromisoformat(data['maturity_date']).date()

        loan.updated_at = datetime.utcnow()
        db.session.commit()

        try:
            regenerate_loan_cash_flows(loan)
        except Exception:
            current_app.logger.exception('Failed to regenerate cash flows for loan %s', loan.id)

        return jsonify(loan.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@bp.route('/<int:loan_id>', methods=['DELETE'])
def delete_loan(loan_id):
    """Delete a loan"""
    loan = Loan.query.get_or_404(loan_id)

    try:
        clear_loan_cash_flows(loan.id, commit=False)
        db.session.delete(loan)
        db.session.commit()
        return jsonify({"message": "Loan deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
