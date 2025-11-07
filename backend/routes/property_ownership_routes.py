from flask import Blueprint, jsonify, request, current_app
from datetime import datetime

from database import db
from models import Property, PropertyOwnershipEvent

bp = Blueprint('property_ownership', __name__)


def _get_property_or_404(property_id):
    return Property.query.get_or_404(property_id)


@bp.route('/api/properties/<int:property_id>/ownership-events', methods=['GET'])
def list_ownership_events(property_id):
    property_obj = _get_property_or_404(property_id)
    events = PropertyOwnershipEvent.query.filter_by(property_id=property_obj.id).order_by(
        PropertyOwnershipEvent.event_date
    ).all()
    return jsonify([event.to_dict() for event in events])


@bp.route('/api/properties/<int:property_id>/ownership-events', methods=['POST'])
def create_ownership_event(property_id):
    property_obj = _get_property_or_404(property_id)
    data = request.get_json() or {}

    if 'event_date' not in data or not data['event_date']:
        return jsonify({'error': 'event_date is required'}), 400
    if 'ownership_percent' not in data:
        return jsonify({'error': 'ownership_percent is required'}), 400

    try:
        event = PropertyOwnershipEvent(
            property_id=property_obj.id,
            event_date=datetime.fromisoformat(data['event_date']).date(),
            ownership_percent=_validate_percent(data['ownership_percent']),
            note=data.get('note')
        )

        property_obj.ownership_percent = event.ownership_percent

        db.session.add(event)
        db.session.commit()

        return jsonify(event.to_dict()), 201
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('Failed to create ownership event for property %s', property_id)
        return jsonify({'error': str(exc)}), 400


@bp.route('/api/properties/<int:property_id>/ownership-events/<int:event_id>', methods=['DELETE'])
def delete_ownership_event(property_id, event_id):
    property_obj = _get_property_or_404(property_id)
    event = PropertyOwnershipEvent.query.filter_by(id=event_id, property_id=property_obj.id).first_or_404()

    try:
        db.session.delete(event)
        db.session.flush()

        latest_event = PropertyOwnershipEvent.query.filter_by(property_id=property_obj.id).order_by(
            PropertyOwnershipEvent.event_date.desc()
        ).first()
        property_obj.ownership_percent = latest_event.ownership_percent if latest_event else None
        db.session.commit()

        return jsonify({'message': 'Ownership event deleted'})
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('Failed to delete ownership event %s for property %s', event_id, property_id)
        return jsonify({'error': str(exc)}), 400


def _validate_percent(value):
    percent = float(value)
    if percent < 0 or percent > 1:
        raise ValueError('ownership_percent must be between 0 and 1')
    return percent
