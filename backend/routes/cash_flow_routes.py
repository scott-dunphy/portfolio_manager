from flask import Blueprint, request, jsonify
from database import db
from models import CashFlow
from datetime import datetime

bp = Blueprint('cash_flows', __name__, url_prefix='/api/cash-flows')

@bp.route('/', methods=['GET'])
def get_cash_flows():
    """Get all cash flows, optionally filtered by portfolio_id"""
    portfolio_id = request.args.get('portfolio_id', type=int)

    if portfolio_id:
        cash_flows = CashFlow.query.filter_by(portfolio_id=portfolio_id).all()
    else:
        cash_flows = CashFlow.query.all()

    return jsonify([cf.to_dict() for cf in cash_flows])

@bp.route('/<int:cash_flow_id>', methods=['GET'])
def get_cash_flow(cash_flow_id):
    """Get a specific cash flow"""
    cash_flow = CashFlow.query.get_or_404(cash_flow_id)
    return jsonify(cash_flow.to_dict())

@bp.route('/', methods=['POST'])
def create_cash_flow():
    """Create a new cash flow"""
    data = request.get_json()

    try:
        cash_flow = CashFlow(
            portfolio_id=data['portfolio_id'],
            property_id=data.get('property_id'),
            loan_id=data.get('loan_id'),
            date=datetime.fromisoformat(data['date']).date(),
            cash_flow_type=data['cash_flow_type'],
            amount=data['amount'],
            description=data.get('description')
        )

        db.session.add(cash_flow)
        db.session.commit()

        return jsonify(cash_flow.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@bp.route('/<int:cash_flow_id>', methods=['PUT'])
def update_cash_flow(cash_flow_id):
    """Update an existing cash flow"""
    cash_flow = CashFlow.query.get_or_404(cash_flow_id)
    data = request.get_json()

    try:
        # Update fields if provided
        for field in ['property_id', 'loan_id', 'cash_flow_type', 'amount', 'description']:
            if field in data:
                setattr(cash_flow, field, data[field])

        if 'date' in data:
            cash_flow.date = datetime.fromisoformat(data['date']).date()

        cash_flow.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(cash_flow.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@bp.route('/<int:cash_flow_id>', methods=['DELETE'])
def delete_cash_flow(cash_flow_id):
    """Delete a cash flow"""
    cash_flow = CashFlow.query.get_or_404(cash_flow_id)

    try:
        db.session.delete(cash_flow)
        db.session.commit()
        return jsonify({"message": "Cash flow deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
