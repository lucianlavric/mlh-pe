from dotenv import load_dotenv
from flask import Flask, jsonify

from app.database import init_db
from app.errors import register_error_handlers
from app.logging_config import setup_logging
from app.routes import register_routes


def create_app(config=None):
    load_dotenv()

    app = Flask(__name__)

    if config:
        app.config.update(config)

    if not app.config.get("TESTING"):
        init_db(app)
        setup_logging(app)

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
        checks = {"status": "ok"}
        if not app.config.get("TESTING"):
            # Deep health check: verify DB and Redis
            try:
                from app.database import db as _db
                _db.execute_sql("SELECT 1")
                checks["database"] = "connected"
            except Exception:
                checks["database"] = "disconnected"
                checks["status"] = "degraded"
            try:
                from app.cache import get_redis
                r = get_redis()
                if r and r.ping():
                    checks["redis"] = "connected"
                else:
                    checks["redis"] = "disconnected"
            except Exception:
                checks["redis"] = "disconnected"
        status_code = 200 if checks["status"] == "ok" else 503
        return jsonify(checks), status_code

    return app
