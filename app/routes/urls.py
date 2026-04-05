import csv
import io
import json
import string
import random
from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect, request
from playhouse.shortcuts import model_to_dict

from app import limiter
from app.cache import cache_delete, cache_get, cache_set
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


def _url_to_dict(url):
    """Serialize a URL to dict with flat user_id and url_id fields."""
    d = model_to_dict(url, recurse=False)
    # Ensure user_id is a flat integer
    d["user_id"] = d.pop("user", url.user_id)
    return d


def _create_url_from_data(data):
    """Shared logic for POST /shorten and POST /urls."""
    if not data or not isinstance(data, dict):
        return jsonify(error="Request body must be JSON"), 400

    # Accept both "url" and "original_url" field names
    original_url = data.get("original_url") or data.get("url", "")
    if isinstance(original_url, str):
        original_url = original_url.strip()
    else:
        original_url = ""

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
    if title and not isinstance(title, str):
        return jsonify(error="title must be a string"), 400

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

    return jsonify(_url_to_dict(url)), 201


@urls_bp.route("/shorten", methods=["POST"])
@limiter.limit("30 per minute")
def shorten_url():
    data = request.get_json(silent=True)
    return _create_url_from_data(data)


@urls_bp.route("/urls", methods=["POST"])
@limiter.limit("30 per minute")
def create_url():
    data = request.get_json(silent=True)
    return _create_url_from_data(data)


@urls_bp.route("/urls/bulk", methods=["POST"])
def bulk_upload_urls():
    if "file" not in request.files:
        return jsonify(error="No file provided"), 400

    file = request.files["file"]
    stream = io.StringIO(file.stream.read().decode("utf-8"))
    reader = csv.DictReader(stream)
    rows = list(reader)

    if not rows:
        return jsonify(error="Empty CSV"), 400

    imported = 0
    with db.atomic():
        for row in rows:
            if "is_active" in row:
                row["is_active"] = row["is_active"] in ("True", "true", "1")
            Url.create(
                user=row.get("user_id"),
                short_code=row.get("short_code", _generate_short_code()),
                original_url=row.get("original_url", ""),
                title=row.get("title", ""),
                is_active=row.get("is_active", True),
                created_at=row.get("created_at", datetime.now(timezone.utc)),
                updated_at=row.get("updated_at", datetime.now(timezone.utc)),
            )
            imported += 1

    return jsonify(count=imported), 201


@urls_bp.route("/<short_code>")
def redirect_short_url(short_code):
    # Try Redis cache first
    cache_key = f"url:{short_code}"
    cached = cache_get(cache_key)
    if cached:
        if not cached["is_active"]:
            return jsonify(error="This short URL has been deactivated"), 410
        # Log redirect event (still need DB for this)
        now = datetime.now(timezone.utc)
        Event.create(
            url=cached["id"],
            user=cached["user_id"],
            event_type="click",
            timestamp=now,
            details=json.dumps({"short_code": short_code, "original_url": cached["original_url"]}),
        )
        return redirect(cached["original_url"], code=302)

    # Cache miss — query DB
    url = Url.get_or_none(Url.short_code == short_code)
    if not url:
        return jsonify(error="Short URL not found"), 404
    if not url.is_active:
        cache_set(cache_key, {"id": url.id, "user_id": url.user_id, "original_url": url.original_url, "is_active": False})
        return jsonify(error="This short URL has been deactivated"), 410

    # Cache the URL for future redirects
    cache_set(cache_key, {"id": url.id, "user_id": url.user_id, "original_url": url.original_url, "is_active": True})

    # The Unseen Observer: log every redirect
    now = datetime.now(timezone.utc)
    Event.create(
        url=url,
        user=url.user,
        event_type="click",
        timestamp=now,
        details=json.dumps({"short_code": url.short_code, "original_url": url.original_url}),
    )

    return redirect(url.original_url, code=302)


@urls_bp.route("/urls")
def list_urls():
    page, per_page = _parse_pagination()
    if page is None:
        return jsonify(error="Invalid pagination parameters"), 400

    query = Url.select().order_by(Url.id)

    # Support ?user_id=X filtering
    user_id = request.args.get("user_id")
    if user_id:
        try:
            query = query.where(Url.user == int(user_id))
        except (ValueError, TypeError):
            return jsonify(error="Invalid user_id filter"), 400

    # Support ?is_active=true/false filtering
    is_active = request.args.get("is_active")
    if is_active is not None:
        if is_active.lower() in ("true", "1"):
            query = query.where(Url.is_active == True)
        elif is_active.lower() in ("false", "0"):
            query = query.where(Url.is_active == False)

    urls = query.paginate(page, per_page)
    return jsonify([_url_to_dict(u) for u in urls])


@urls_bp.route("/urls/<int:url_id>")
def get_url(url_id):
    url = Url.get_or_none(Url.id == url_id)
    if not url:
        return jsonify(error="URL not found"), 404
    return jsonify(_url_to_dict(url))


@urls_bp.route("/urls/code/<short_code>")
def get_url_by_code(short_code):
    url = Url.get_or_none(Url.short_code == short_code)
    if not url:
        return jsonify(error="URL not found"), 404
    return jsonify(_url_to_dict(url))


@urls_bp.route("/urls/<int:url_id>", methods=["PUT"])
def update_url(url_id):
    url = Url.get_or_none(Url.id == url_id)
    if not url:
        return jsonify(error="URL not found"), 404

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify(error="Request body must be JSON"), 400

    changes = {}

    if "url" in data or "original_url" in data:
        new_url = data.get("original_url") or data.get("url")
        if not _is_valid_url(new_url):
            return jsonify(error="Invalid URL. Must start with http:// or https://"), 400
        url.original_url = new_url.strip()
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

    # Invalidate cache
    cache_delete(f"url:{url.short_code}")

    return jsonify(_url_to_dict(url))


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

    # Invalidate cache
    cache_delete(f"url:{url.short_code}")

    return jsonify(_url_to_dict(url)), 200
