from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from redis import Redis
import pika
import json
from marshmallow import Schema, fields, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# налаштування
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['REDIS_HOST'] = 'localhost'

db = SQLAlchemy(app)
jwt = JWTManager(app)
redis = Redis(host='localhost', port=6379, db=0)


# моделі
class User(db.Model):
    """Модель пользователя с именем и захешированным паролем."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class BuySellConditionsSchema(Schema):
    """Схема для валидации условий покупки и продажи."""
    indicator = fields.Str(required=True)
    threshold = fields.Float(required=True)


class StrategySchema(Schema):
    """Схема для валидации стратегии торговли."""
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    asset_type = fields.Str(required=True)
    buy_conditions = fields.Nested(BuySellConditionsSchema, required=True)
    sell_conditions = fields.Nested(BuySellConditionsSchema, required=True)
    status = fields.Str(required=True, validate=lambda x: x in ['active', 'inactive'])


class Strategy(db.Model):
    """Модель стратегии торговли с условиями покупки и продажи."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)
    buy_conditions = db.Column(db.JSON, nullable=False)
    sell_conditions = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('strategies', lazy=True))


# Функции для RabbitMQ
def send_message_to_rabbitmq(message):
    """Отправляет сообщение в RabbitMQ."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='strategy_updates')
    channel.basic_publish(exchange='', routing_key='strategy_updates', body=message)
    connection.close()


# Роут для регистрации пользователя
@app.route('/auth/register', methods=['POST'])
def register():
    """Регистрация нового пользователя с паролем."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify(message="Username and password are required"), 400

    # Проверка на существующего пользователя
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify(message="Username already exists"), 400

    # Хеширование пароля
    hashed_password = generate_password_hash(password)

    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify(message="User registered successfully"), 201


@app.route('/auth/login', methods=['POST'])
def login():
    """Авторизация пользователя и получение JWT токена."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify(message="Username and password are required"), 400

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, password):
        access_token = create_access_token(identity=user.username)
        return jsonify(access_token=access_token)
    else:
        return jsonify(message="Invalid credentials"), 401


# Роут для создания стратегии
@app.route('/strategies', methods=['POST'])
@jwt_required()
def create_strategy():
    """Создание новой стратегии торговли."""
    data = request.get_json()

    # Валидация данных
    try:
        validated_data = StrategySchema().load(data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify(message="User not found"), 404

    new_strategy = Strategy(
        name=validated_data['name'],
        description=validated_data['description'],
        asset_type=validated_data['asset_type'],
        buy_conditions=validated_data['buy_conditions'],
        sell_conditions=validated_data['sell_conditions'],
        status=validated_data['status'],
        user_id=user.id  # Назначаем стратегию пользователю
    )
    db.session.add(new_strategy)
    db.session.commit()

    # Отправить сообщение в RabbitMQ
    message = json.dumps({"message": f"User {user.username} created strategy {new_strategy.name}"})
    send_message_to_rabbitmq(message)

    # Обновить кэш в Redis
    redis.delete(f"user_strategies:{user.id}")

    return jsonify(message="Strategy created successfully"), 201


@app.route('/strategies', methods=['GET'])
@jwt_required()
def get_strategies():
    """Получение всех стратегий текущего пользователя."""
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify(message="User not found"), 404

    # Проверяем наличие кэша в Redis
    cached_strategies = redis.get(f"user_strategies:{user.id}")
    if cached_strategies:
        return jsonify(json.loads(cached_strategies)), 200

    strategies = Strategy.query.filter_by(user_id=user.id).all()

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

    # Кэшируем стратегии в Redis
    redis.set(f"user_strategies:{user.id}", json.dumps(result), ex=60 * 60)  # Кэш на 1 час

    return jsonify(result), 200


@app.route('/strategies/<int:id>', methods=['PUT'])
@jwt_required()
def update_strategy(id):
    """Обновление стратегии по ее ID."""
    strategy = Strategy.query.filter_by(id=id).first()

    if strategy is None:
        return jsonify(message="Strategy not found"), 404

    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()

    if not user or strategy.user_id != user.id:
        return jsonify(message="You can only update your own strategies"), 403

    data = request.get_json()

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

    # Отправка сообщения в RabbitMQ
    message = json.dumps({"message": f"User {user.username} updated strategy {strategy.name}"})
    send_message_to_rabbitmq(message)

    redis.delete(f"user_strategies:{user.id}")

    return jsonify(message="Strategy updated successfully"), 200


@app.route('/strategies/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_strategy(id):
    """Удаление стратегии по ее ID."""
    strategy = Strategy.query.filter_by(id=id).first()

    if strategy is None:
        return jsonify(message="Strategy not found"), 404

    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()

    if not user or strategy.user_id != user.id:
        return jsonify(message="You can only delete your own strategies"), 403

    db.session.delete(strategy)
    db.session.commit()

    message = json.dumps({"message": f"User {user.username} deleted strategy {strategy.name}"})
    send_message_to_rabbitmq(message)

    redis.delete(f"user_strategies:{user.id}")

    return jsonify(message="Strategy deleted successfully"), 200


# Роут для симуляции стратегии
@app.route('/strategies/<int:id>/simulate', methods=['POST'])
@jwt_required()
def simulate_strategy(id):
    """Симуляция стратегии на основе исторических данных."""
    data = request.get_json()

    if not data or not isinstance(data, list):
        return jsonify(message="Historical data is required"), 400

    # Получение стратегии
    strategy = Strategy.query.filter_by(id=id).first()
    if not strategy:
        return jsonify(message="Strategy not found"), 404

    # Проверка прав доступа
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user or strategy.user_id != user.id:
        return jsonify(message="You can only simulate your own strategies"), 403

    # Начальные параметры
    total_trades = 0
    profit_loss = 0.0
    win_trades = 0
    max_drawdown = 0.0
    initial_balance = 10000.0
    balance = initial_balance
    highest_balance = initial_balance

    # Логика симуляции
    for day in data:
        try:
            date = day['date']
            close_price = day['close']
            volume = day.get('volume', 1)  # По умолчанию объем = 1
        except KeyError:
            print(f"Skipping day due to missing data: {day}", flush=True)
            continue

        # Логика покупки
        buy_signal = False
        if strategy.buy_conditions['indicator'] == "momentum" and close_price > strategy.buy_conditions['threshold']:
            buy_signal = True

        # Логика продажи
        sell_signal = False
        if strategy.sell_conditions['indicator'] == "momentum" and close_price < strategy.sell_conditions['threshold']:
            sell_signal = True

        # Если сработал сигнал на покупку
        if buy_signal:
            total_trades += 1
            balance -= close_price * volume  # Покупаем по цене закрытия с учетом объема
            print(f"Buy on {date}: close={close_price}, volume={volume}, balance={balance}", flush=True)

        # Если сработал сигнал на продажу
        if sell_signal:
            total_trades += 1
            balance += close_price * volume  # Продаем по цене закрытия с учетом объема
            win_trades += 1
            print(f"Sell on {date}: close={close_price}, volume={volume}, balance={balance}", flush=True)

        # Расчет максимальной просадки
        if balance > highest_balance:
            highest_balance = balance
        drawdown = (highest_balance - balance) / highest_balance * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    # Итоги симуляции
    profit_loss = balance - initial_balance
    win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0

    result = {
        "strategy_id": id,
        "total_trades": total_trades,
        "profit_loss": round(profit_loss, 2),
        "win_rate": round(win_rate, 2),
        "max_drawdown": round(max_drawdown, 2)
    }

    return jsonify(result), 200

# Функция для создания таблиц в базе данных
def create_tables():
    """Создает все таблицы в базе данных на основе моделей."""
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    create_tables()
    app.run(debug=True, port=5001)
