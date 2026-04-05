import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask.json.provider import DefaultJSONProvider
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.database import init_db
from app.errors import register_error_handlers
from app.logging_config import setup_logging
from app.routes import register_routes


class ISOJSONProvider(DefaultJSONProvider):
    """Return datetimes in ISO 8601 format instead of RFC 2822."""
    @staticmethod
    def default(o):
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%dT%H:%M:%S")
        return DefaultJSONProvider.default(o)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per minute"],
    storage_uri=os.environ.get("REDIS_URL", "memory://"),
)


def create_app(config=None):
    load_dotenv()

    app = Flask(__name__)
    app.json_provider_class = ISOJSONProvider
    app.json = ISOJSONProvider(app)

    if config:
        app.config.update(config)

    if not app.config.get("TESTING"):
        init_db(app)
        setup_logging(app)
        limiter.init_app(app)

    from app.models import Event, Url, User  # noqa: F401 - registers models

    if not app.config.get("TESTING"):
        from app.database import db
        db.connect(reuse_if_open=True)
        db.create_tables([User, Url, Event])
        db.close()

    register_routes(app)
    register_error_handlers(app)

    @app.route("/health")
    def health():
        from datetime import datetime, timezone
        checks = {
            "status": "ok",
            "version": "1.0.0",
            "instance": os.environ.get("INSTANCE_ID", "local"),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if not app.config.get("TESTING"):
            dependencies = {}
            try:
                from app.database import db as _db
                _db.execute_sql("SELECT 1")
                dependencies["database"] = {"status": "connected"}
            except Exception:
                dependencies["database"] = {"status": "disconnected"}
                checks["status"] = "degraded"
            try:
                from app.cache import get_redis
                r = get_redis()
                if r and r.ping():
                    dependencies["redis"] = {"status": "connected"}
                else:
                    dependencies["redis"] = {"status": "disconnected"}
            except Exception:
                dependencies["redis"] = {"status": "disconnected"}
            checks["dependencies"] = dependencies
            # Keep flat fields for backward compatibility with tests
            checks["database"] = dependencies.get("database", {}).get("status", "unknown")
            checks["redis"] = dependencies.get("redis", {}).get("status", "unknown")
        status_code = 200 if checks["status"] == "ok" else 503
        return jsonify(checks), status_code

    return app
