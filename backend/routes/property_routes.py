from flask import Blueprint, request, jsonify, current_app
from database import db
from models import Property, PropertyOwnershipEvent, Portfolio, PropertyManualCashFlow, Loan
from datetime import datetime, date
from services.cash_flow_service import (
    clear_property_cash_flows,
    regenerate_property_cash_flows,
    regenerate_loan_cash_flows,
)
from services.property_valuation_service import calculate_property_valuation

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

    results = [
        _serialize_property(prop, include_manual=include_manual, include_ownership=include_ownership)
        for prop in properties
    ]

    return jsonify(results)

@bp.route('/<int:property_id>', methods=['GET'])
def get_property(property_id):
    """Get a specific property"""
    property_obj = Property.query.get_or_404(property_id)
    return jsonify(
        _serialize_property(
            property_obj,
            include_manual=True,
            include_ownership=True,
            include_loans=True,
        )
    )

@bp.route('', methods=['POST'])
def create_property():
    """Create a new property"""
    data = request.get_json()

    try:
        ownership_percent = _normalize_percent(_parse_float(data.get('ownership_percent'), 'ownership_percent'))
        exit_cap_rate = _parse_float(data.get('exit_cap_rate'), 'exit_cap_rate')
        if exit_cap_rate is None or exit_cap_rate <= 0:
            raise ValueError("exit_cap_rate is required and must be greater than 0")
        market_value_start = _parse_float(data.get('market_value_start'), 'market_value_start')
        if market_value_start is None or market_value_start <= 0:
            raise ValueError("market_value_start is required and must be greater than 0")
        encumbrance_override = _parse_bool(data.get('encumbrance_override'), False)
        encumbrance_note = (data.get('encumbrance_note') or '').strip()
        if encumbrance_override and not encumbrance_note:
            raise ValueError("encumbrance_note is required when encumbrance_override is enabled")
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
            exit_cap_rate=exit_cap_rate,
            building_size=_parse_float(data.get('building_size'), 'building_size'),
            noi_growth_rate=_parse_float(data.get('noi_growth_rate'), 'noi_growth_rate'),
            initial_noi=_parse_float(data.get('initial_noi'), 'initial_noi'),
            valuation_method=data.get('valuation_method', 'growth'),
            ownership_percent=ownership_percent,
            capex_percent_of_noi=_parse_float(data.get('capex_percent_of_noi'), 'capex_percent_of_noi'),
            use_manual_noi_capex=_parse_bool(data.get('use_manual_noi_capex'), False),
            market_value_start=market_value_start,
            disposition_price_override=_parse_float(
                data.get('disposition_price_override'), 'disposition_price_override'
            ),
            encumbrance_override=encumbrance_override,
            encumbrance_note=encumbrance_note or None,
        )

        db.session.add(property)
        db.session.flush()

        _sync_baseline_ownership_event(property)
        valuation = _recalculate_property_metrics(property)
        db.session.commit()

        try:
            _ensure_initial_ownership_event(property)
        except Exception:
            current_app.logger.exception('Failed to create initial ownership event for property %s', property.id)

        try:
            regenerate_property_cash_flows(property)
        except Exception:
            current_app.logger.exception('Failed to regenerate property cash flows for property %s', property.id)

        try:
            _regenerate_loans_for_property(property.id)
        except Exception:
            current_app.logger.exception('Failed to regenerate loan cash flows for property %s', property.id)

        return jsonify(
            _serialize_property(
                property,
                include_manual=True,
                include_ownership=True,
                include_loans=True,
                valuation=valuation,
            )
        ), 201
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
            'building_size',
            'noi_growth_rate',
            'initial_noi',
            'ownership_percent',
            'capex_percent_of_noi',
            'market_value_start',
            'disposition_price_override',
        }
        for field in ['property_name', 'property_type', 'address', 'city', 'state', 'zip_code',
                      'purchase_price', 'exit_cap_rate', 'building_size',
                      'noi_growth_rate', 'initial_noi', 'valuation_method', 'ownership_percent',
                      'capex_percent_of_noi', 'use_manual_noi_capex', 'market_value_start',
                      'disposition_price_override', 'encumbrance_override', 'encumbrance_note']:
            if field in data:
                value = data[field]
                if field in numeric_fields:
                    value = _parse_float(value, field)
                    if field == 'exit_cap_rate' and (value is None or value <= 0):
                        raise ValueError("exit_cap_rate must be greater than 0")
                    if field == 'market_value_start':
                        if value is None or value <= 0:
                            raise ValueError("market_value_start must be greater than 0")
                if field == 'ownership_percent':
                    value = _normalize_percent(value, default=property.ownership_percent or 1.0)
                if field == 'use_manual_noi_capex':
                    value = _parse_bool(value, default=property.use_manual_noi_capex)
                if field == 'encumbrance_override':
                    value = _parse_bool(value, default=bool(property.encumbrance_override))
                if field == 'encumbrance_note' and isinstance(value, str):
                    value = value.strip()
                    if value == '':
                        value = None
                setattr(property, field, value)

        if property.encumbrance_override and not (property.encumbrance_note or '').strip():
            raise ValueError("encumbrance_note is required when encumbrance_override is enabled")

        if 'purchase_date' in data and data['purchase_date']:
            property.purchase_date = datetime.fromisoformat(data['purchase_date']).date()
        if 'exit_date' in data and data['exit_date']:
            property.exit_date = datetime.fromisoformat(data['exit_date']).date()

        property.updated_at = datetime.utcnow()
        _sync_baseline_ownership_event(property)
        valuation = _recalculate_property_metrics(property)
        db.session.commit()

        try:
            regenerate_property_cash_flows(property)
        except Exception:
            current_app.logger.exception('Failed to regenerate property cash flows for property %s', property.id)

        try:
            _regenerate_loans_for_property(property.id)
        except Exception:
            current_app.logger.exception('Failed to regenerate loan cash flows for property %s', property.id)

        return jsonify(
            _serialize_property(
                property,
                include_manual=True,
                include_ownership=True,
                include_loans=True,
                valuation=valuation,
            )
        )
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
        _recalculate_property_metrics(property)

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


@bp.route('/types', methods=['GET'])
def list_property_types():
    portfolio_id = request.args.get('portfolio_id', type=int)
    query = db.session.query(Property.property_type).filter(Property.property_type.isnot(None))
    if portfolio_id:
        query = query.filter(Property.portfolio_id == portfolio_id)
    types = sorted({(row[0] or '').strip() for row in query.distinct() if (row[0] or '').strip()})
    types.append('Unassigned')
    return jsonify(types)


def _regenerate_loans_for_property(property_id: int) -> None:
    loans = Loan.query.filter_by(property_id=property_id).all()
    if not loans:
        return
    for loan in loans:
        regenerate_loan_cash_flows(loan, commit=False)
    db.session.commit()


def _serialize_property(property_obj, include_manual=False, include_ownership=False, include_loans=False, valuation=None):
    data = property_obj.to_dict()
    if not include_manual:
        data.pop('manual_cash_flows', None)
    if not include_ownership:
        data.pop('ownership_events', None)
    if include_loans:
        data['loans'] = [
            {
                'id': loan.id,
                'loan_name': loan.loan_name,
                'loan_id': loan.loan_id,
                'loan_type': loan.loan_type,
                'principal_amount': loan.principal_amount,
                'interest_rate': loan.interest_rate,
                'maturity_date': loan.maturity_date.isoformat() if loan.maturity_date else None,
            }
            for loan in getattr(property_obj, 'loans', []) or []
        ]
    else:
        data.pop('loans', None)
    if valuation is None:
        valuation = calculate_property_valuation(property_obj)
    data['calculated_year1_cap_rate'] = valuation['year1_cap_rate']
    data['monthly_market_values'] = valuation['monthly_market_values']
    encumbrance_periods = _get_encumbrance_periods(property_obj)
    data['encumbrance_periods'] = encumbrance_periods
    data['has_active_loan'] = _has_active_loan(encumbrance_periods)
    data['is_encumbered'] = _is_property_encumbered(property_obj, encumbrance_periods)
    return data


def _recalculate_property_metrics(property_obj):
    valuation = calculate_property_valuation(property_obj)
    property_obj.year_1_cap_rate = valuation['year1_cap_rate']
    return valuation


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


def _has_active_loan(encumbrance_periods) -> bool:
    today = date.today()
    for period in encumbrance_periods:
        if period.get('manual'):
            continue
        start = _parse_iso_date(period.get('start_date'))
        end = _parse_iso_date(period.get('end_date'))
        if not start or not end:
            continue
        if start <= today <= end:
            return True
    return False


def _is_property_encumbered(property_obj: Property, encumbrance_periods) -> bool:
    if property_obj.encumbrance_override:
        return True
    return _has_active_loan(encumbrance_periods)


def _parse_iso_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _get_encumbrance_periods(property_obj: Property):
    loans = getattr(property_obj, 'loans', None)
    if loans is None:
        loans = Loan.query.filter_by(property_id=property_obj.id).all()
    periods = []
    for loan in loans or []:
        if loan.property_id != property_obj.id:
            continue
        if not loan.origination_date or not loan.maturity_date:
            continue
        if loan.maturity_date < loan.origination_date:
            continue
        periods.append({
            'start_date': loan.origination_date.isoformat(),
            'end_date': loan.maturity_date.isoformat(),
            'loan_id': loan.id
        })
    if property_obj.encumbrance_override:
        periods.append({'start_date': None, 'end_date': None, 'manual': True})
    return periods
    return False


def _is_property_encumbered(property_obj: Property) -> bool:
    if property_obj.encumbrance_override:
        return True
    return _has_active_loan(property_obj)
