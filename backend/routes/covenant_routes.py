from flask import Blueprint, jsonify, request

from services.covenant_service import build_covenant_metrics

bp = Blueprint('covenants', __name__, url_prefix='/api/covenants')


@bp.route('', methods=['GET'])
def get_covenants():
    portfolio_id = request.args.get('portfolio_id', type=int)
    if not portfolio_id:
        return jsonify({"error": "portfolio_id is required"}), 400

    apply_ownership = request.args.get('apply_ownership', '0') == '1'

    try:
        data = build_covenant_metrics(portfolio_id, apply_ownership=apply_ownership)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(data)
