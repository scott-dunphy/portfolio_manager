from flask import Blueprint, request, jsonify
from database import db
from models import Loan
from datetime import datetime

bp = Blueprint('loans', __name__, url_prefix='/api/loans')

@bp.route('/', methods=['GET'])
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

@bp.route('/', methods=['POST'])
def create_loan():
    """Create a new loan"""
    data = request.get_json()

    try:
        loan = Loan(
            portfolio_id=data['portfolio_id'],
            property_id=data.get('property_id'),
            loan_id=data['loan_id'],
            loan_name=data['loan_name'],
            principal_amount=data['principal_amount'],
            interest_rate=data['interest_rate'],
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
        # Update fields if provided
        for field in ['loan_name', 'principal_amount', 'interest_rate', 'payment_frequency',
                      'loan_type', 'amortization_period_months', 'io_period_months',
                      'origination_fee', 'exit_fee', 'property_id']:
            if field in data:
                setattr(loan, field, data[field])

        if 'origination_date' in data:
            loan.origination_date = datetime.fromisoformat(data['origination_date']).date()
        if 'maturity_date' in data:
            loan.maturity_date = datetime.fromisoformat(data['maturity_date']).date()

        loan.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(loan.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@bp.route('/<int:loan_id>', methods=['DELETE'])
def delete_loan(loan_id):
    """Delete a loan"""
    loan = Loan.query.get_or_404(loan_id)

    try:
        db.session.delete(loan)
        db.session.commit()
        return jsonify({"message": "Loan deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
