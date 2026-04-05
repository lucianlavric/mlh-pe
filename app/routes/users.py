import csv
import io
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict

from app.database import db
from app.models.user import User

users_bp = Blueprint("users", __name__)


def _parse_pagination():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        if page < 1 or per_page < 1:
            raise ValueError
        return page, per_page
    except (ValueError, TypeError):
        return None, None


@users_bp.route("/users")
def list_users():
    page, per_page = _parse_pagination()
    if page is None:
        return jsonify(error="Invalid pagination parameters"), 400
    users = User.select().order_by(User.id).paginate(page, per_page)
    return jsonify([model_to_dict(u) for u in users])


@users_bp.route("/users/<int:user_id>")
def get_user(user_id):
    user = User.get_or_none(User.id == user_id)
    if not user:
        return jsonify(error="User not found"), 404
    return jsonify(model_to_dict(user))


@users_bp.route("/users", methods=["POST"])
def create_user():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify(error="Request body must be JSON"), 400

    username = data.get("username")
    email = data.get("email")

    if not username or not isinstance(username, str):
        return jsonify(error="Invalid or missing username"), 400
    if not email or not isinstance(email, str):
        return jsonify(error="Invalid or missing email"), 400

    now = datetime.now(timezone.utc)
    user = User.create(
        username=username,
        email=email,
        created_at=now,
    )
    return jsonify(model_to_dict(user)), 201


@users_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = User.get_or_none(User.id == user_id)
    if not user:
        return jsonify(error="User not found"), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify(error="Request body must be JSON"), 400

    if "username" in data:
        if not isinstance(data["username"], str):
            return jsonify(error="username must be a string"), 400
        user.username = data["username"]

    if "email" in data:
        if not isinstance(data["email"], str):
            return jsonify(error="email must be a string"), 400
        user.email = data["email"]

    user.save()
    return jsonify(model_to_dict(user))


@users_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = User.get_or_none(User.id == user_id)
    if not user:
        return jsonify(error="User not found"), 404
    user.delete_instance()
    return "", 204


@users_bp.route("/users/bulk", methods=["POST"])
def bulk_upload_users():
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
            User.create(
                username=row.get("username", ""),
                email=row.get("email", ""),
                created_at=row.get("created_at", datetime.now(timezone.utc)),
            )
            imported += 1

    return jsonify(count=imported), 201
