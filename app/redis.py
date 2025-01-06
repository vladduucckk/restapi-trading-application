from redis import Redis
import json

redis = Redis(host='localhost', port=6379, db=0)

def get_cached_strategies(user_id):
    """Отримання стратегій з кешу Redis."""
    cached_strategies = redis.get(f"user_strategies:{user_id}")
    if cached_strategies:
        return json.loads(cached_strategies)
    return None

def cache_strategies(user_id, strategies):
    """Кешування стратегій Redis."""
    redis.set(f"user_strategies:{user_id}", json.dumps(strategies), ex=60 * 60)  # Кеш на 1 час
