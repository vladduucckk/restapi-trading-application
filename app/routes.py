from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from . import app
from .models import User
from .services.auth_service import AuthService
from .services.strategy_service import StrategyService
from .services.simulation_service import SimulationService

@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    return AuthService.register(data)

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    return AuthService.login(data)

@app.route('/strategies', methods=['POST'])
@jwt_required()
def create_strategy():
    data = request.get_json()
    if not data:
        return jsonify(message="No data provided"), 400

    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify(message="User not found"), 404

    return StrategyService.create_strategy(data, user)

@app.route('/strategies', methods=['GET'])
@jwt_required()
def get_strategies():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    return StrategyService.get_strategies(user)

@app.route('/strategies/<int:id>', methods=['PUT'])
@jwt_required()
def update_strategy(id):
    data = request.get_json()
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    return StrategyService.update_strategy(id, data, user)

@app.route('/strategies/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_strategy(id):
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    return StrategyService.delete_strategy(id, user)

@app.route('/strategies/<int:id>/simulate', methods=['POST'])
@jwt_required()
def simulate_strategy(id):
    data = request.get_json()
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    return SimulationService.simulate_strategy(id, data, user)