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

# Налаштування додатку
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['REDIS_HOST'] = 'localhost'

db = SQLAlchemy(app)
jwt = JWTManager(app)
redis = Redis(host='localhost', port=6379, db=0)


# Моделі бази даних

class User(db.Model):
    """Модель користувача з іменем та захешованим паролем."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class BuySellConditionsSchema(Schema):
    """Схема для валідації умов покупки та продажу."""
    indicator = fields.Str(required=True)
    threshold = fields.Float(required=True)


class StrategySchema(Schema):
    """Схема для валідації стратегії торгівлі."""
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    asset_type = fields.Str(required=True)
    buy_conditions = fields.Nested(BuySellConditionsSchema, required=True)
    sell_conditions = fields.Nested(BuySellConditionsSchema, required=True)
    status = fields.Str(required=True, validate=lambda x: x in ['active', 'inactive'])


class Strategy(db.Model):
    """Модель стратегії торгівлі з умовами покупки та продажу."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)
    buy_conditions = db.Column(db.JSON, nullable=False)
    sell_conditions = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('strategies', lazy=True))


# Функції для роботи з RabbitMQ
def send_message_to_rabbitmq(message):
    """Відправляє повідомлення в RabbitMQ."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='strategy_updates')
    channel.basic_publish(exchange='', routing_key='strategy_updates', body=message)
    connection.close()


# Роут для реєстрації користувача
@app.route('/auth/register', methods=['POST'])
def register():
    """Реєстрація нового користувача з паролем."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify(message="Username and password are required"), 400

    # Перевірка на наявність користувача
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify(message="Username already exists"), 400

    # Хешування пароля
    hashed_password = generate_password_hash(password)

    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify(message="User registered successfully"), 201


@app.route('/auth/login', methods=['POST'])
def login():
    """Авторизація користувача та отримання JWT токена."""
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


# Роут для створення стратегії
@app.route('/strategies', methods=['POST'])
@jwt_required()
def create_strategy():
    """Створення нової стратегії торгівлі."""
    data = request.get_json()

    # Валідація даних
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
        user_id=user.id  # Призначаємо стратегію користувачу
    )
    db.session.add(new_strategy)
    db.session.commit()

    # Відправка повідомлення в RabbitMQ
    message = json.dumps({"message": f"User {user.username} created strategy {new_strategy.name}"})
    send_message_to_rabbitmq(message)

    # Оновлення кешу в Redis
    redis.delete(f"user_strategies:{user.id}")

    return jsonify(message="Strategy created successfully"), 201


@app.route('/strategies', methods=['GET'])
@jwt_required()
def get_strategies():
    """Отримання всіх стратегій поточного користувача."""
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify(message="User not found"), 404

    # Перевірка наявності кешу в Redis
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

    # Кешування стратегій в Redis
    redis.set(f"user_strategies:{user.id}", json.dumps(result), ex=60 * 60)  # Кеш на 1 годину

    return jsonify(result), 200


@app.route('/strategies/<int:id>', methods=['PUT'])
@jwt_required()
def update_strategy(id):
    """Оновлення стратегії за її ID."""
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

    # Відправка повідомлення в RabbitMQ
    message = json.dumps({"message": f"User {user.username} updated strategy {strategy.name}"})
    send_message_to_rabbitmq(message)

    redis.delete(f"user_strategies:{user.id}")

    return jsonify(message="Strategy updated successfully"), 200


@app.route('/strategies/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_strategy(id):
    """Видалення стратегії за її ID."""
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


# Роут для симуляції стратегії
@app.route('/strategies/<int:id>/simulate', methods=['POST'])
@jwt_required()
def simulate_strategy(id):
    """Симуляція стратегії на основі історичних даних."""
    data = request.get_json()

    if not data or not isinstance(data, list):
        return jsonify(message="Historical data is required"), 400

    # Отримання стратегії
    strategy = Strategy.query.filter_by(id=id).first()
    if not strategy:
        return jsonify(message="Strategy not found"), 404

    # Перевірка прав доступу
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user or strategy.user_id != user.id:
        return jsonify(message="You can only simulate your own strategies"), 403

    # Початкові параметри
    total_trades = 0
    profit_loss = 0.0
    win_trades = 0
    max_drawdown = 0.0
    initial_balance = 10000.0
    balance = initial_balance
    highest_balance = initial_balance

    # Логіка симуляції
    for day in data:
        try:
            date = day['date']
            close_price = day['close']
            volume = day.get('volume', 1)  # За замовчуванням об'єм = 1
        except KeyError:
            print(f"Skipping day due to missing data: {day}", flush=True)
            continue

        # Логіка покупки
        buy_signal = False
        if strategy.buy_conditions['indicator'] == "momentum" and close_price > strategy.buy_conditions['threshold']:
            buy_signal = True

        # Логіка продажу
        sell_signal = False
        if strategy.sell_conditions['indicator'] == "momentum" and close_price < strategy.sell_conditions['threshold']:
            sell_signal = True

        # Якщо спрацював сигнал на покупку
        if buy_signal:
            total_trades += 1
            balance -= close_price * volume  # Купуємо по ціні закриття з урахуванням об'єму
            print(f"Buy on {date}: close={close_price}, volume={volume}, balance={balance}", flush=True)

        # Якщо спрацював сигнал на продаж
        if sell_signal:
            total_trades += 1
            balance += close_price * volume  # Продаємо по ціні закриття з урахуванням об'єму
            win_trades += 1
            print(f"Sell on {date}: close={close_price}, volume={volume}, balance={balance}", flush=True)

        # Розрахунок максимальної просадки
        if balance > highest_balance:
            highest_balance = balance
        drawdown = (highest_balance - balance) / highest_balance * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    # Результати симуляції
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


# Функція для створення таблиць у базі даних
def create_tables():
    """Створює всі таблиці в базі даних на основі моделей."""
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    create_tables()
    app.run(debug=True, port=5001)
