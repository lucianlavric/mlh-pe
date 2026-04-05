import json
import os

import redis


_client = None


def get_redis():
    global _client
    if _client is None:
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            try:
                _client = redis.from_url(redis_url, decode_responses=True)
                _client.ping()
            except (redis.ConnectionError, redis.TimeoutError):
                _client = None
    return _client


def cache_get(key):
    r = get_redis()
    if r is None:
        return None
    try:
        val = r.get(key)
        if val:
            return json.loads(val)
    except (redis.ConnectionError, redis.TimeoutError):
        pass
    return None


def cache_set(key, value, ttl=300):
    r = get_redis()
    if r is None:
        return
    try:
        r.set(key, json.dumps(value), ex=ttl)
    except (redis.ConnectionError, redis.TimeoutError):
        pass


def cache_delete(key):
    r = get_redis()
    if r is None:
        return
    try:
        r.delete(key)
    except (redis.ConnectionError, redis.TimeoutError):
        pass
