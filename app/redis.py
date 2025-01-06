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
    strategies_data = [{
        'id': strategy.id,
        'name': strategy.name,
        'description': strategy.description,
        'asset_type': strategy.asset_type,
        'buy_conditions': strategy.buy_conditions,
        'sell_conditions': strategy.sell_conditions,
        'status': strategy.status
    } for strategy in strategies]

    redis.set(f"user_strategies:{user_id}", json.dumps(strategies_data), ex=60 * 60)
