import json
import logging
import os
import time

from flask import g, request


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "instance": os.environ.get("INSTANCE_ID", "local"),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging(app):
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    app.logger.handlers = []
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    logging.getLogger("werkzeug").handlers = []
    logging.getLogger("werkzeug").addHandler(handler)

    @app.before_request
    def _log_request_start():
        g.start_time = time.time()

    @app.after_request
    def _log_request_end(response):
        duration = time.time() - getattr(g, "start_time", time.time())
        app.logger.info(
            json.dumps({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "level": "INFO",
                "type": "request",
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "instance": os.environ.get("INSTANCE_ID", "local"),
            })
        )
        return response
