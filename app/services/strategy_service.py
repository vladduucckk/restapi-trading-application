from marshmallow import ValidationError
from .. import redis
import json
from app import db
from app.models import Strategy, User
from app.schemas import StrategySchema
from app.redis import cache_strategies


class StrategyService:
    @staticmethod
    def create_strategy(data, username):
        try:
            validated_data = StrategySchema().load(data)
        except ValidationError as err:
            return err.messages, 400

        user = User.query.filter_by(username=username).first()
        if not user:
            return {"message": "User not found"}, 404

        new_strategy = Strategy(
            name=validated_data['name'],
            description=validated_data['description'],
            asset_type=validated_data['asset_type'],
            buy_conditions=validated_data['buy_conditions'],
            sell_conditions=validated_data['sell_conditions'],
            status=validated_data['status'],
            user_id=user.id
        )
        db.session.add(new_strategy)
        db.session.commit()

        # Get all strategies to pass to cache_strategies
        strategies = Strategy.query.filter_by(user_id=user.id).all()

        # Оновлення кешу
        cache_strategies(user.id, strategies)

        return {"message": "Strategy created successfully"}, 201

    @staticmethod
    def get_strategies(user_id):
        cached_strategies = redis.get(f"user_strategies:{user_id}")
        if cached_strategies:
            return json.loads(cached_strategies), 200

        strategies = Strategy.query.filter_by(user_id=user_id).all()
        result = []
        for strategy in strategies:
            result.append({
                'id': strategy.id,
                'name': strategy.name,
                'description': strategy.description,
                'asset_type': strategy.asset_type,
                'buy_conditions': strategy.buy_conditions,
                'sell_conditions': strategy.sell_conditions,
                'status': strategy.status
            })

        # Кешування
        redis.set(f"user_strategies:{user_id}", json.dumps(result), ex=60 * 60)  # Кеш на 1 годину
        return result, 200

    @staticmethod
    def update_strategy(id, data, username):
        strategy = Strategy.query.filter_by(id=id).first()

        if strategy is None:
            return {"message": "Strategy not found"}, 404

        user = User.query.filter_by(username=username).first()
        if not user or strategy.user_id != user.id:
            return {"message": "You can only update your own strategies"}, 403

        try:
            validated_data = StrategySchema().load(data)
        except ValidationError as err:
            return err.messages, 400

        strategy.name = validated_data['name']
        strategy.description = validated_data['description']
        strategy.asset_type = validated_data['asset_type']
        strategy.buy_conditions = validated_data['buy_conditions']
        strategy.sell_conditions = validated_data['sell_conditions']
        strategy.status = validated_data['status']

        db.session.commit()

        # Оновлення кешу
        cache_strategies(user.id)

        return {"message": "Strategy updated successfully"}, 200

    @staticmethod
    def delete_strategy(id, username):
        strategy = Strategy.query.filter_by(id=id).first()

        if strategy is None:
            return {"message": "Strategy not found"}, 404

        user = User.query.filter_by(username=username).first()
        if not user or strategy.user_id != user.id:
            return {"message": "You can only delete your own strategies"}, 403

        db.session.delete(strategy)
        db.session.commit()

        # Оновлення кешу
        cache_strategies(user.id)

        return {"message": "Strategy deleted successfully"}, 200
