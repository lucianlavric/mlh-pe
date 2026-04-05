import json
import string
import random
from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, redirect, request
from playhouse.shortcuts import model_to_dict

from app.database import db
from app.models.event import Event
from app.models.url import Url
from app.models.user import User

urls_bp = Blueprint("urls", __name__)

SHORT_CODE_LENGTH = 6
SHORT_CODE_CHARS = string.ascii_letters + string.digits


def _generate_short_code():
    """Generate a unique short code."""
    for _ in range(10):
        code = "".join(random.choices(SHORT_CODE_CHARS, k=SHORT_CODE_LENGTH))
        if not Url.select().where(Url.short_code == code).exists():
            return code
    return None


def _parse_pagination():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        if page < 1 or per_page < 1:
            raise ValueError
        return page, per_page
    except (ValueError, TypeError):
        return None, None


def _is_valid_url(url):
    """Basic URL validation."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return False
    if len(url) < 10:
        return False
    return True


@urls_bp.route("/shorten", methods=["POST"])
def shorten_url():
    data = request.get_json(silent=True)
    if not data:
        return jsonify(error="Request body must be JSON"), 400

    original_url = data.get("url", "").strip() if isinstance(data.get("url"), str) else ""
    if not _is_valid_url(original_url):
        return jsonify(error="Invalid or missing URL. Must start with http:// or https://"), 400

    user_id = data.get("user_id")
    if user_id is not None:
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return jsonify(error="Invalid user_id"), 400
        user = User.get_or_none(User.id == user_id)
        if not user:
            return jsonify(error="User not found"), 404
    else:
        return jsonify(error="user_id is required"), 400

    short_code = data.get("short_code")
    if short_code:
        if not isinstance(short_code, str) or len(short_code) < 1:
            return jsonify(error="Invalid short_code"), 400
        if Url.select().where(Url.short_code == short_code).exists():
            return jsonify(error="Short code already exists"), 409
    else:
        short_code = _generate_short_code()
        if not short_code:
            return jsonify(error="Could not generate unique short code"), 500

    title = data.get("title", "")

    now = datetime.now(timezone.utc)

    with db.atomic():
        url = Url.create(
            user=user_id,
            short_code=short_code,
            original_url=original_url,
            title=title,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        Event.create(
            url=url,
            user=user_id,
            event_type="created",
            timestamp=now,
            details=json.dumps({"short_code": short_code, "original_url": original_url}),
        )

    return jsonify(model_to_dict(url)), 201


@urls_bp.route("/<short_code>")
def redirect_short_url(short_code):
    url = Url.get_or_none(Url.short_code == short_code)
    if not url:
        return jsonify(error="Short URL not found"), 404
    if not url.is_active:
        return jsonify(error="This short URL has been deactivated"), 410

    # The Unseen Observer: log every redirect
    now = datetime.now(timezone.utc)
    Event.create(
        url=url,
        user=url.user,
        event_type="redirect",
        timestamp=now,
        details=json.dumps({"short_code": url.short_code, "original_url": url.original_url}),
    )

    return redirect(url.original_url, code=302)


@urls_bp.route("/urls")
def list_urls():
    page, per_page = _parse_pagination()
    if page is None:
        return jsonify(error="Invalid pagination parameters"), 400
    urls = Url.select().order_by(Url.id).paginate(page, per_page)
    return jsonify([model_to_dict(u) for u in urls])


@urls_bp.route("/urls/<int:url_id>")
def get_url(url_id):
    url = Url.get_or_none(Url.id == url_id)
    if not url:
        return jsonify(error="URL not found"), 404
    return jsonify(model_to_dict(url))


@urls_bp.route("/urls/code/<short_code>")
def get_url_by_code(short_code):
    url = Url.get_or_none(Url.short_code == short_code)
    if not url:
        return jsonify(error="URL not found"), 404
    return jsonify(model_to_dict(url))


@urls_bp.route("/urls/<int:url_id>", methods=["PUT"])
def update_url(url_id):
    url = Url.get_or_none(Url.id == url_id)
    if not url:
        return jsonify(error="URL not found"), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify(error="Request body must be JSON"), 400

    changes = {}

    if "url" in data:
        if not _is_valid_url(data["url"]):
            return jsonify(error="Invalid URL. Must start with http:// or https://"), 400
        url.original_url = data["url"].strip()
        changes["original_url"] = url.original_url

    if "title" in data:
        url.title = data["title"]
        changes["title"] = url.title

    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            return jsonify(error="is_active must be a boolean"), 400
        url.is_active = data["is_active"]
        changes["is_active"] = url.is_active

    if not changes:
        return jsonify(error="No valid fields to update"), 400

    now = datetime.now(timezone.utc)
    url.updated_at = now

    with db.atomic():
        url.save()
        Event.create(
            url=url,
            user=url.user,
            event_type="updated",
            timestamp=now,
            details=json.dumps(changes),
        )

    return jsonify(model_to_dict(url))


@urls_bp.route("/urls/<int:url_id>", methods=["DELETE"])
def delete_url(url_id):
    url = Url.get_or_none(Url.id == url_id)
    if not url:
        return jsonify(error="URL not found"), 404

    now = datetime.now(timezone.utc)

    with db.atomic():
        url.is_active = False
        url.updated_at = now
        url.save()
        Event.create(
            url=url,
            user=url.user,
            event_type="deleted",
            timestamp=now,
            details=json.dumps({"short_code": url.short_code}),
        )

    return jsonify(message="URL deactivated"), 200
