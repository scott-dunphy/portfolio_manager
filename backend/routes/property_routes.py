from flask import Blueprint, request, jsonify, current_app
from database import db
from models import Property, PropertyOwnershipEvent, Portfolio, PropertyManualCashFlow
from datetime import datetime, date
from services.cash_flow_service import (
    clear_property_cash_flows,
    regenerate_property_cash_flows,
)

bp = Blueprint('properties', __name__, url_prefix='/api/properties')

def _parse_float(value, field_name):
    """Return None for empty strings, otherwise coerce to float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    value_str = str(value).strip()
    if value_str == '':
        return None
    try:
        return float(value_str)
    except ValueError as exc:
        raise ValueError(f"Invalid value for {field_name}: {value}") from exc

def _normalize_percent(value, default=1.0):
    if value is None:
        return default
    if value < 0 or value > 1:
        raise ValueError("ownership_percent must be between 0 and 1")
    return value

def _parse_int(value, field_name):
    """Require a value and coerce it to int."""
    if value is None:
        raise ValueError(f"{field_name} is required")
    if isinstance(value, int):
        return value
    value_str = str(value).strip()
    if value_str == '':
        raise ValueError(f"{field_name} is required")
    try:
        return int(value_str)
    except ValueError as exc:
        raise ValueError(f"Invalid value for {field_name}: {value}") from exc

@bp.route('', methods=['GET'])
def get_properties():
    """Get all properties, optionally filtered by portfolio_id"""
    portfolio_id = request.args.get('portfolio_id', type=int)

    if portfolio_id:
        properties = Property.query.filter_by(portfolio_id=portfolio_id).all()
    else:
        properties = Property.query.all()

    include_manual = request.args.get('include_manual', '0') == '1'
    include_ownership = request.args.get('include_ownership', '0') == '1'

    results = []
    for prop in properties:
        data = prop.to_dict()
        if not include_manual:
            data.pop('manual_cash_flows', None)
        if not include_ownership:
            data.pop('ownership_events', None)
        results.append(data)

    return jsonify(results)

@bp.route('/<int:property_id>', methods=['GET'])
def get_property(property_id):
    """Get a specific property"""
    property = Property.query.get_or_404(property_id)
    return jsonify(property.to_dict())

@bp.route('', methods=['POST'])
def create_property():
    """Create a new property"""
    data = request.get_json()

    try:
        ownership_percent = _normalize_percent(_parse_float(data.get('ownership_percent'), 'ownership_percent'))
        property = Property(
            portfolio_id=_parse_int(data['portfolio_id'], 'portfolio_id'),
            property_id=data['property_id'],
            property_name=data['property_name'],
            property_type=data.get('property_type'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            zip_code=data.get('zip_code'),
            purchase_price=_parse_float(data.get('purchase_price'), 'purchase_price'),
            purchase_date=datetime.fromisoformat(data['purchase_date']).date() if data.get('purchase_date') else None,
            exit_date=datetime.fromisoformat(data['exit_date']).date() if data.get('exit_date') else None,
            exit_cap_rate=_parse_float(data.get('exit_cap_rate'), 'exit_cap_rate'),
            year_1_cap_rate=_parse_float(data.get('year_1_cap_rate'), 'year_1_cap_rate'),
            building_size=_parse_float(data.get('building_size'), 'building_size'),
            noi_growth_rate=_parse_float(data.get('noi_growth_rate'), 'noi_growth_rate'),
            initial_noi=_parse_float(data.get('initial_noi'), 'initial_noi'),
            valuation_method=data.get('valuation_method', 'growth'),
            ownership_percent=ownership_percent,
            capex_percent_of_noi=_parse_float(data.get('capex_percent_of_noi'), 'capex_percent_of_noi'),
            use_manual_noi_capex=_parse_bool(data.get('use_manual_noi_capex'), False)
        )

        db.session.add(property)
        db.session.flush()

        _sync_baseline_ownership_event(property)
        db.session.commit()

        try:
            _ensure_initial_ownership_event(property)
        except Exception:
            current_app.logger.exception('Failed to create initial ownership event for property %s', property.id)

        try:
            regenerate_property_cash_flows(property)
        except Exception:
            current_app.logger.exception('Failed to regenerate property cash flows for property %s', property.id)

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
        numeric_fields = {
            'purchase_price',
            'exit_cap_rate',
            'year_1_cap_rate',
            'building_size',
            'noi_growth_rate',
            'initial_noi',
            'ownership_percent',
            'capex_percent_of_noi'
        }
        for field in ['property_name', 'property_type', 'address', 'city', 'state', 'zip_code',
                      'purchase_price', 'exit_cap_rate', 'year_1_cap_rate', 'building_size',
                      'noi_growth_rate', 'initial_noi', 'valuation_method', 'ownership_percent',
                      'capex_percent_of_noi', 'use_manual_noi_capex']:
            if field in data:
                value = data[field]
                if field in numeric_fields:
                    value = _parse_float(value, field)
                if field == 'ownership_percent':
                    value = _normalize_percent(value, default=property.ownership_percent or 1.0)
                if field == 'use_manual_noi_capex':
                    value = _parse_bool(value, default=property.use_manual_noi_capex)
                setattr(property, field, value)

        if 'purchase_date' in data and data['purchase_date']:
            property.purchase_date = datetime.fromisoformat(data['purchase_date']).date()
        if 'exit_date' in data and data['exit_date']:
            property.exit_date = datetime.fromisoformat(data['exit_date']).date()

        property.updated_at = datetime.utcnow()
        _sync_baseline_ownership_event(property)
        db.session.commit()

        try:
            regenerate_property_cash_flows(property)
        except Exception:
            current_app.logger.exception('Failed to regenerate property cash flows for property %s', property.id)

        return jsonify(property.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@bp.route('/<int:property_id>', methods=['DELETE'])
def delete_property(property_id):
    """Delete a property"""
    property = Property.query.get_or_404(property_id)

    try:
        clear_property_cash_flows(property.id, commit=False)
        db.session.delete(property)
        db.session.commit()
        return jsonify({"message": "Property deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@bp.route('/<int:property_id>/manual-cash-flows', methods=['PUT'])
def upsert_manual_cash_flows(property_id):
    property = Property.query.get_or_404(property_id)
    data = request.get_json() or {}
    entries = data.get('entries', [])
    use_manual = data.get('use_manual_noi_capex')

    try:
        PropertyManualCashFlow.query.filter_by(property_id=property_id).delete()
        manual_rows = []
        for entry in entries:
            year = entry.get('year')
            if year is None:
                continue
            manual_rows.append(
                PropertyManualCashFlow(
                    property_id=property_id,
                    year=int(year),
                    annual_noi=_parse_float(entry.get('annual_noi'), 'annual_noi'),
                    annual_capex=_parse_float(entry.get('annual_capex'), 'annual_capex')
                )
            )
        property.manual_cash_flows = manual_rows

        if use_manual is not None:
            property.use_manual_noi_capex = _parse_bool(use_manual, default=property.use_manual_noi_capex)

        property.updated_at = datetime.utcnow()

        try:
            regenerate_property_cash_flows(property)
        except Exception:
            current_app.logger.exception('Failed to regenerate property cash flows for property %s', property.id)

        db.session.commit()
        return jsonify({
            "manual_cash_flows": [row.to_dict() for row in property.manual_cash_flows],
            "use_manual_noi_capex": property.use_manual_noi_capex
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@bp.route('/<int:property_id>/manual-cash-flows', methods=['GET'])
def list_manual_cash_flows(property_id):
    property = Property.query.get_or_404(property_id)
    return jsonify([row.to_dict() for row in property.manual_cash_flows])


def _sync_baseline_ownership_event(property_obj: Property):
    portfolio = property_obj.portfolio or Portfolio.query.get(property_obj.portfolio_id)
    start_date = (
        portfolio.analysis_start_date if portfolio and portfolio.analysis_start_date else None
    )
    if not start_date:
        start_date = property_obj.purchase_date
    if not start_date:
        start_date = date.today()

    percent = property_obj.ownership_percent if property_obj.ownership_percent is not None else 1.0

    existing_events = list(property_obj.ownership_events)

    if not existing_events:
        event = PropertyOwnershipEvent(
            property_id=property_obj.id,
            event_date=start_date,
            ownership_percent=percent,
            note='Initial ownership'
        )
        db.session.add(event)
    elif len(existing_events) == 1:
        event = existing_events[0]
        event.event_date = start_date
        event.ownership_percent = percent
        if not event.note:
            event.note = 'Initial ownership'
def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    value_str = str(value).strip().lower()
    if value_str in {'1', 'true', 't', 'yes', 'on'}:
        return True
    if value_str in {'0', 'false', 'f', 'no', 'off'}:
        return False
    return default
