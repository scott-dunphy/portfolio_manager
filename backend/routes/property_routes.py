from flask import Blueprint, request, jsonify
from database import db
from models import Property
from datetime import datetime

bp = Blueprint('properties', __name__, url_prefix='/api/properties')

@bp.route('/', methods=['GET'])
def get_properties():
    """Get all properties, optionally filtered by portfolio_id"""
    portfolio_id = request.args.get('portfolio_id', type=int)

    if portfolio_id:
        properties = Property.query.filter_by(portfolio_id=portfolio_id).all()
    else:
        properties = Property.query.all()

    return jsonify([p.to_dict() for p in properties])

@bp.route('/<int:property_id>', methods=['GET'])
def get_property(property_id):
    """Get a specific property"""
    property = Property.query.get_or_404(property_id)
    return jsonify(property.to_dict())

@bp.route('/', methods=['POST'])
def create_property():
    """Create a new property"""
    data = request.get_json()

    try:
        property = Property(
            portfolio_id=data['portfolio_id'],
            property_id=data['property_id'],
            property_name=data['property_name'],
            property_type=data.get('property_type'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            zip_code=data.get('zip_code'),
            purchase_price=data.get('purchase_price'),
            purchase_date=datetime.fromisoformat(data['purchase_date']).date() if data.get('purchase_date') else None,
            exit_date=datetime.fromisoformat(data['exit_date']).date() if data.get('exit_date') else None,
            exit_cap_rate=data.get('exit_cap_rate'),
            year_1_cap_rate=data.get('year_1_cap_rate'),
            building_size=data.get('building_size'),
            noi_growth_rate=data.get('noi_growth_rate'),
            initial_noi=data.get('initial_noi'),
            valuation_method=data.get('valuation_method', 'growth')
        )

        db.session.add(property)
        db.session.commit()

        return jsonify(property.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@bp.route('/<int:property_id>', methods=['PUT'])
def update_property(property_id):
    """Update an existing property"""
    property = Property.query.get_or_404(property_id)
    data = request.get_json()

    try:
        # Update fields if provided
        for field in ['property_name', 'property_type', 'address', 'city', 'state', 'zip_code',
                      'purchase_price', 'exit_cap_rate', 'year_1_cap_rate', 'building_size',
                      'noi_growth_rate', 'initial_noi', 'valuation_method']:
            if field in data:
                setattr(property, field, data[field])

        if 'purchase_date' in data and data['purchase_date']:
            property.purchase_date = datetime.fromisoformat(data['purchase_date']).date()
        if 'exit_date' in data and data['exit_date']:
            property.exit_date = datetime.fromisoformat(data['exit_date']).date()

        property.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(property.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@bp.route('/<int:property_id>', methods=['DELETE'])
def delete_property(property_id):
    """Delete a property"""
    property = Property.query.get_or_404(property_id)

    try:
        db.session.delete(property)
        db.session.commit()
        return jsonify({"message": "Property deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
