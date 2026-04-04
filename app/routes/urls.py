from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict

from app.models.url import Url

urls_bp = Blueprint("urls", __name__)


def _parse_pagination():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        if page < 1 or per_page < 1:
            raise ValueError
        return page, per_page
    except (ValueError, TypeError):
        return None, None


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
