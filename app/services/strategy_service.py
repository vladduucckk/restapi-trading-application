from marshmallow import ValidationError
from werkzeug.exceptions import BadRequest

from .. import db
from ..models import Strategy
from ..schemas import StrategySchema
from flask import jsonify
from ..redis import get_cached_strategies, cache_strategies
from ..rabbitmq import send_message_to_rabbitmq
import json

class StrategyService:
    @staticmethod
    def create_strategy(data, user):
        if not data:
            raise BadRequest("No data provided")

        # Перевірка на валідність даних за допомогою схеми
        try:
            validated_data = StrategySchema().load(data)
        except ValidationError as err:
            return jsonify(err.messages), 400

        # Перевірка наявності всіх необхідних полів
        if 'name' not in validated_data or 'description' not in validated_data:
            return jsonify(message="Missing required fields: name or description"), 400

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

        return jsonify(message="Strategy created successfully"), 201

    @staticmethod
    def get_strategies(user):
        cached_strategies = get_cached_strategies(user.id)
        if cached_strategies:
            return jsonify(cached_strategies), 200

        strategies = Strategy.query.filter_by(user_id=user.id).all()
        result = [{
            'id': strategy.id,
            'name': strategy.name,
            'description': strategy.description,
            'asset_type': strategy.asset_type,
            'buy_conditions': strategy.buy_conditions,
            'sell_conditions': strategy.sell_conditions,
            'status': strategy.status
        } for strategy in strategies]

        cache_strategies(user.id, result)

        return jsonify(result), 200

    @staticmethod
    def update_strategy(id, data, user):
        strategy = Strategy.query.filter_by(id=id).first()

        if strategy is None:
            return jsonify(message="Strategy not found"), 404

        if strategy.user_id != user.id:
            return jsonify(message="You can only update your own strategies"), 403

        try:
            validated_data = StrategySchema().load(data)
        except ValidationError as err:
            return jsonify(err.messages), 400

        strategy.name = validated_data['name']
        strategy.description = validated_data['description']
        strategy.asset_type = validated_data['asset_type']
        strategy.buy_conditions = validated_data['buy_conditions']
        strategy.sell_conditions = validated_data['sell_conditions']
        strategy.status = validated_data['status']

        db.session.commit()

        message = json.dumps({"message": f"User {user.username} updated strategy {strategy.name}"})
        send_message_to_rabbitmq(message)

        cache_strategies(user.id, strategy)

        return jsonify(message="Strategy updated successfully"), 200

    @staticmethod
    def delete_strategy(id, user):
        strategy = Strategy.query.filter_by(id=id).first()

        if strategy is None:
            return jsonify(message="Strategy not found"), 404

        if strategy.user_id != user.id:
            return jsonify(message="You can only delete your own strategies"), 403

        db.session.delete(strategy)
        db.session.commit()

        message = json.dumps({"message": f"User {user.username} deleted strategy {strategy.name}"})
        send_message_to_rabbitmq(message)

        cache_strategies(user.id, [])

        return jsonify(message="Strategy deleted successfully"), 200