import json

from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict

from app.models.event import Event

events_bp = Blueprint("events", __name__)


def _parse_pagination():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        if page < 1 or per_page < 1:
            raise ValueError
        return page, per_page
    except (ValueError, TypeError):
        return None, None


def _event_to_dict(event):
    """Serialize event with flat url_id/user_id and parsed details."""
    d = model_to_dict(event, recurse=False)
    d["url_id"] = d.pop("url", event.url_id)
    d["user_id"] = d.pop("user", event.user_id)
    # Parse details from JSON string to object
    if isinstance(d.get("details"), str):
        try:
            d["details"] = json.loads(d["details"])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


@events_bp.route("/events")
def list_events():
    page, per_page = _parse_pagination()
    if page is None:
        return jsonify(error="Invalid pagination parameters"), 400
    query = Event.select().order_by(Event.id).paginate(page, per_page)
    return jsonify([_event_to_dict(e) for e in query])


@events_bp.route("/events/<int:event_id>")
def get_event(event_id):
    event = Event.get_or_none(Event.id == event_id)
    if not event:
        return jsonify(error="Event not found"), 404
    return jsonify(_event_to_dict(event))
