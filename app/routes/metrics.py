import os
import time

from flask import Blueprint, jsonify

from app.database import db
from app.models.event import Event
from app.models.url import Url
from app.models.user import User

metrics_bp = Blueprint("metrics", __name__)

_start_time = time.time()


@metrics_bp.route("/metrics")
def metrics():
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        memory_mb = usage.ru_maxrss / (1024 * 1024)  # macOS reports bytes
        cpu_user = usage.ru_utime
        cpu_system = usage.ru_stime
    except Exception:
        memory_mb = 0
        cpu_user = 0
        cpu_system = 0

    # Database stats
    try:
        total_users = User.select().count()
        total_urls = Url.select().count()
        active_urls = Url.select().where(Url.is_active == True).count()
        total_events = Event.select().count()
        redirect_events = Event.select().where(Event.event_type == "click").count()
    except Exception:
        total_users = total_urls = active_urls = total_events = redirect_events = 0

    # Redis stats
    redis_status = "disconnected"
    redis_keys = 0
    try:
        from app.cache import get_redis
        r = get_redis()
        if r:
            redis_status = "connected"
            redis_keys = r.dbsize()
    except Exception:
        pass

    uptime = time.time() - _start_time

    return jsonify({
        "uptime_seconds": round(uptime, 2),
        "instance": os.environ.get("INSTANCE_ID", "local"),
        "system": {
            "memory_mb": round(memory_mb, 2),
            "cpu_user_seconds": round(cpu_user, 2),
            "cpu_system_seconds": round(cpu_system, 2),
        },
        "database": {
            "total_users": total_users,
            "total_urls": total_urls,
            "active_urls": active_urls,
            "total_events": total_events,
            "redirect_events": redirect_events,
        },
        "cache": {
            "status": redis_status,
            "cached_keys": redis_keys,
        },
    })
