from flask import Blueprint, request, jsonify
from database import db
from models import Portfolio
from datetime import datetime

bp = Blueprint('portfolios', __name__, url_prefix='/api/portfolios')

@bp.route('', methods=['GET'])
def get_portfolios():
    """Get all portfolios"""
    portfolios = Portfolio.query.all()
    return jsonify([p.to_dict() for p in portfolios])

@bp.route('/<int:portfolio_id>', methods=['GET'])
def get_portfolio(portfolio_id):
    """Get a specific portfolio"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    result = portfolio.to_dict()
    # Include related data
    result['properties'] = [p.to_dict() for p in portfolio.properties]
    result['loans'] = [l.to_dict() for l in portfolio.loans]
    result['preferred_equities'] = [pe.to_dict() for pe in portfolio.preferred_equities]
    return jsonify(result)

@bp.route('', methods=['POST'])
def create_portfolio():
    """Create a new portfolio"""
    data = request.get_json()

    try:
        portfolio = Portfolio(
            name=data['name'],
            analysis_start_date=datetime.fromisoformat(data['analysis_start_date']).date(),
            analysis_end_date=datetime.fromisoformat(data['analysis_end_date']).date(),
            initial_unfunded_equity=data.get('initial_unfunded_equity', 0.0),
            beginning_cash=data.get('beginning_cash', 0.0),
            fee=data.get('fee', 0.0),
            beginning_nav=data.get('beginning_nav', 0.0),
            valuation_method=data.get('valuation_method', 'growth')
        )

        db.session.add(portfolio)
        db.session.commit()

        return jsonify(portfolio.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@bp.route('/<int:portfolio_id>', methods=['PUT'])
def update_portfolio(portfolio_id):
    """Update an existing portfolio"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    data = request.get_json()

    try:
        if 'name' in data:
            portfolio.name = data['name']
        if 'analysis_start_date' in data:
            portfolio.analysis_start_date = datetime.fromisoformat(data['analysis_start_date']).date()
        if 'analysis_end_date' in data:
            portfolio.analysis_end_date = datetime.fromisoformat(data['analysis_end_date']).date()
        if 'initial_unfunded_equity' in data:
            portfolio.initial_unfunded_equity = data['initial_unfunded_equity']
        if 'beginning_cash' in data:
            portfolio.beginning_cash = data['beginning_cash']
        if 'fee' in data:
            portfolio.fee = data['fee']
        if 'beginning_nav' in data:
            portfolio.beginning_nav = data['beginning_nav']
        if 'valuation_method' in data:
            portfolio.valuation_method = data['valuation_method']

        portfolio.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(portfolio.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@bp.route('/<int:portfolio_id>', methods=['DELETE'])
def delete_portfolio(portfolio_id):
    """Delete a portfolio"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)

    try:
        db.session.delete(portfolio)
        db.session.commit()
        return jsonify({"message": "Portfolio deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
