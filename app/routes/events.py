import json

from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict

from datetime import datetime, timezone

from app.models.event import Event
from app.models.url import Url
from app.models.user import User

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
    query = Event.select().order_by(Event.id)

    url_id = request.args.get("url_id")
    if url_id:
        try:
            query = query.where(Event.url == int(url_id))
        except (ValueError, TypeError):
            return jsonify(error="Invalid url_id filter"), 400

    user_id = request.args.get("user_id")
    if user_id:
        try:
            query = query.where(Event.user == int(user_id))
        except (ValueError, TypeError):
            return jsonify(error="Invalid user_id filter"), 400

    event_type = request.args.get("event_type")
    if event_type:
        query = query.where(Event.event_type == event_type)

    events = query.paginate(page, per_page)
    return jsonify([_event_to_dict(e) for e in events])


@events_bp.route("/events", methods=["POST"])
def create_event():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify(error="Request body must be JSON"), 400

    url_id = data.get("url_id")
    user_id = data.get("user_id")
    event_type = data.get("event_type")

    if not url_id or not user_id or not event_type:
        return jsonify(error="url_id, user_id, and event_type are required"), 400

    if not isinstance(event_type, str):
        return jsonify(error="event_type must be a string"), 400

    if isinstance(url_id, (bool, float)) or isinstance(user_id, (bool, float)):
        return jsonify(error="Invalid url_id or user_id"), 400
    try:
        url_id = int(url_id)
        user_id = int(user_id)
    except (ValueError, TypeError):
        return jsonify(error="Invalid url_id or user_id"), 400

    if not Url.get_or_none(Url.id == url_id):
        return jsonify(error="URL not found"), 404
    if not User.get_or_none(User.id == user_id):
        return jsonify(error="User not found"), 404

    details = data.get("details", {})
    if not isinstance(details, dict):
        return jsonify(error="details must be a JSON object"), 400
    details = json.dumps(details)

    event = Event.create(
        url=url_id,
        user=user_id,
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        details=details,
    )
    return jsonify(_event_to_dict(event)), 201


@events_bp.route("/events/<int:event_id>")
def get_event(event_id):
    event = Event.get_or_none(Event.id == event_id)
    if not event:
        return jsonify(error="Event not found"), 404
    return jsonify(_event_to_dict(event))


@events_bp.route("/events/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    event = Event.get_or_none(Event.id == event_id)
    if not event:
        return jsonify(error="Event not found"), 404
    event.delete_instance()
    return "", 204
