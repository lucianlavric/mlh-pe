from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict

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
