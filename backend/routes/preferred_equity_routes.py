from flask import Blueprint, request, jsonify
from database import db
from models import PreferredEquity
from datetime import datetime

bp = Blueprint('preferred_equities', __name__, url_prefix='/api/preferred-equities')

@bp.route('/', methods=['GET'])
def get_preferred_equities():
    """Get all preferred equities, optionally filtered by portfolio_id"""
    portfolio_id = request.args.get('portfolio_id', type=int)

    if portfolio_id:
        pref_equities = PreferredEquity.query.filter_by(portfolio_id=portfolio_id).all()
    else:
        pref_equities = PreferredEquity.query.all()

    return jsonify([pe.to_dict() for pe in pref_equities])

@bp.route('/<int:pref_equity_id>', methods=['GET'])
def get_preferred_equity(pref_equity_id):
    """Get a specific preferred equity"""
    pref_equity = PreferredEquity.query.get_or_404(pref_equity_id)
    return jsonify(pref_equity.to_dict())

@bp.route('/', methods=['POST'])
def create_preferred_equity():
    """Create a new preferred equity"""
    data = request.get_json()

    try:
        pref_equity = PreferredEquity(
            portfolio_id=data['portfolio_id'],
            property_id=data.get('property_id'),
            pref_equity_id=data['pref_equity_id'],
            name=data['name'],
            initial_investment=data['initial_investment'],
            preferred_return=data['preferred_return'],
            investment_date=datetime.fromisoformat(data['investment_date']).date(),
            redemption_date=datetime.fromisoformat(data['redemption_date']).date() if data.get('redemption_date') else None
        )

        db.session.add(pref_equity)
        db.session.commit()

        return jsonify(pref_equity.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@bp.route('/<int:pref_equity_id>', methods=['PUT'])
def update_preferred_equity(pref_equity_id):
    """Update an existing preferred equity"""
    pref_equity = PreferredEquity.query.get_or_404(pref_equity_id)
    data = request.get_json()

    try:
        # Update fields if provided
        for field in ['name', 'initial_investment', 'preferred_return', 'property_id']:
            if field in data:
                setattr(pref_equity, field, data[field])

        if 'investment_date' in data:
            pref_equity.investment_date = datetime.fromisoformat(data['investment_date']).date()
        if 'redemption_date' in data and data['redemption_date']:
            pref_equity.redemption_date = datetime.fromisoformat(data['redemption_date']).date()

        pref_equity.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(pref_equity.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@bp.route('/<int:pref_equity_id>', methods=['DELETE'])
def delete_preferred_equity(pref_equity_id):
    """Delete a preferred equity"""
    pref_equity = PreferredEquity.query.get_or_404(pref_equity_id)

    try:
        db.session.delete(pref_equity)
        db.session.commit()
        return jsonify({"message": "Preferred equity deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
