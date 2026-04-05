"""
RFC 7807-inspired error responses with traceability.
All errors include request_id, timestamp, and path for debugging.
"""

from datetime import datetime, timezone

from flask import g, jsonify, request


def _error_response(status_code, error, message=None):
    """Build a structured error response following PE best practices."""
    body = {
        "error": error,
        "status": status_code,
        "message": message or error,
        "path": request.path if request else None,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "request_id": getattr(g, "request_id", None),
    }
    return jsonify(body), status_code


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return _error_response(400, "Bad request")

    @app.errorhandler(404)
    def not_found(e):
        return _error_response(404, "Not found")

    @app.errorhandler(405)
    def method_not_allowed(e):
        return _error_response(405, "Method not allowed")

    @app.errorhandler(429)
    def rate_limited(e):
        return _error_response(429, "Rate limit exceeded. Try again later.")

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"Internal error on {request.path}: {e}")
        return _error_response(500, "Internal server error")
