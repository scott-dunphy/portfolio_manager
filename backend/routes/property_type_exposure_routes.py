from flask import Blueprint, jsonify, send_file
from models import Portfolio
from services.property_type_exposure_service import calculate_property_type_exposure, get_portfolio_transactions
from services.exposure_export_service import export_property_type_exposure_to_excel

bp = Blueprint('property_type_exposure', __name__, url_prefix='/api')

@bp.route('/portfolios/<int:portfolio_id>/property-type-exposure', methods=['GET'])
def get_property_type_exposure(portfolio_id):
    """
    Get property type exposure over time for a portfolio along with transactions.
    Uses market value at share for the calculation.

    Returns:
    {
        "dates": ["2024-03-31", "2024-06-30", ...],
        "property_types": ["Apartment", "Office", ...],
        "data": [
            {
                "date": "2024-03-31",
                "Apartment": {"percentage": 75.5, "market_value": 1500000},
                "Office": {"percentage": 24.5, "market_value": 500000}
            },
            ...
        ],
        "transactions": [
            {
                "transaction_date": "2024-01-15",
                "property_name": "Downtown Apartments",
                "property_type": "Apartment",
                "transaction_type": "acquisition",
                "transaction_price": 2000000
            },
            ...
        ]
    }
    """
    portfolio = Portfolio.query.get_or_404(portfolio_id)

    try:
        exposure_data = calculate_property_type_exposure(portfolio_id)
        transactions = get_portfolio_transactions(portfolio_id)

        return jsonify({
            **exposure_data,
            "transactions": transactions
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.route('/portfolios/<int:portfolio_id>/property-type-exposure/export', methods=['GET'])
def export_property_type_exposure(portfolio_id):
    """
    Download property type exposure data as an Excel file.
    """
    portfolio = Portfolio.query.get_or_404(portfolio_id)

    try:
        exposure_data = calculate_property_type_exposure(portfolio_id)
        transactions = get_portfolio_transactions(portfolio_id)

        # Combine data
        full_data = {
            **exposure_data,
            "transactions": transactions
        }

        # Generate Excel file
        excel_stream = export_property_type_exposure_to_excel(full_data, portfolio.name)

        # Return file
        return send_file(
            excel_stream,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'Property_Type_Exposure_{portfolio.name.replace(" ", "_")}.xlsx'
        ), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
