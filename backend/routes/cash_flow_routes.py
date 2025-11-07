from flask import Blueprint, request, jsonify, send_file
from database import db
from models import CashFlow, Loan
from datetime import datetime, date
from services.sofr_client import get_forward_rate
from services.cash_flow_report_service import build_cash_flow_report

bp = Blueprint('cash_flows', __name__, url_prefix='/api/cash-flows')

@bp.route('', methods=['GET'])
def get_cash_flows():
    """Get all cash flows, optionally filtered by portfolio_id"""
    portfolio_id = request.args.get('portfolio_id', type=int)
    property_id = request.args.get('property_id', type=int)
    loan_id = request.args.get('loan_id', type=int)

    query = CashFlow.query

    if portfolio_id is not None:
        query = query.filter_by(portfolio_id=portfolio_id)
    if property_id is not None:
        query = query.filter_by(property_id=property_id)
    if loan_id is not None:
        query = query.filter_by(loan_id=loan_id)

    cash_flows = query.all()

    loan_ids = {cf.loan_id for cf in cash_flows if cf.loan_id}
    loans = Loan.query.filter(Loan.id.in_(loan_ids)).all() if loan_ids else []
    loan_map = {loan.id: loan for loan in loans}

    if loan_map:
        changed = _recalculate_floating_interest(cash_flows, loan_map)
        if changed:
            db.session.commit()

    response = []
    for cf in cash_flows:
        cf_dict = cf.to_dict()
        loan = loan_map.get(cf.loan_id)
        if (
            loan
            and (loan.rate_type or '').lower() == 'floating'
            and cf.cash_flow_type == 'loan_interest'
        ):
            forward_rate = get_forward_rate(cf.date) if cf.date else None
            spread = loan.sofr_spread or 0.0
            total_rate = (forward_rate or 0.0) + spread
            cf_dict['floating_rate_data'] = {
                'sofr_rate': forward_rate,
                'spread': spread,
                'total_rate': total_rate
            }
        response.append(cf_dict)

    return jsonify(response)

@bp.route('/export', methods=['GET'])
def export_cash_flows():
    portfolio_id = request.args.get('portfolio_id', type=int)
    if not portfolio_id:
        return jsonify({"error": "portfolio_id is required"}), 400

    report = build_cash_flow_report(portfolio_id)
    filename = f'portfolio_{portfolio_id}_cash_flows.xlsx'
    return send_file(
        report,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@bp.route('/<int:cash_flow_id>', methods=['GET'])
def get_cash_flow(cash_flow_id):
    """Get a specific cash flow"""
    cash_flow = CashFlow.query.get_or_404(cash_flow_id)
    return jsonify(cash_flow.to_dict())

@bp.route('', methods=['POST'])
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


FLOW_SORT_ORDER = {
    'loan_funding': 0,
    'loan_interest': 1,
    'loan_principal': 2,
}


def _recalculate_floating_interest(cash_flows, loan_map):
    flows_by_loan = {}
    for cf in cash_flows:
        loan = loan_map.get(cf.loan_id)
        if not loan:
            continue
        if (loan.rate_type or '').lower() != 'floating':
            continue
        flows_by_loan.setdefault(loan.id, []).append(cf)

    if not flows_by_loan:
        return False

    changed = False

    for loan_id, flows in flows_by_loan.items():
        loan = loan_map[loan_id]
        months_per_period = {
            'monthly': 1,
            'quarterly': 3,
            'annually': 12
        }.get((loan.payment_frequency or 'monthly').lower(), 1)

        balance = 0.0
        sorted_flows = sorted(
            flows,
            key=lambda cf: (
                cf.date or date.min,
                FLOW_SORT_ORDER.get(cf.cash_flow_type, 99),
                cf.id or 0,
            ),
        )

        for cf in sorted_flows:
            cf_type = cf.cash_flow_type
            if cf_type == 'loan_funding':
                balance += cf.amount or 0.0
            elif cf_type == 'loan_principal':
                balance += cf.amount or 0.0
            elif cf_type == 'loan_interest':
                forward_rate = get_forward_rate(cf.date) if cf.date else None
                spread = loan.sofr_spread or 0.0
                annual_rate = (forward_rate or 0.0) + spread
                periodic_rate = annual_rate * months_per_period / 12.0
                recalculated = -(balance or 0.0) * periodic_rate
                if abs((cf.amount or 0.0) - recalculated) > 0.01:
                    cf.amount = recalculated
                    cf.updated_at = datetime.utcnow()
                    changed = True

    return changed
