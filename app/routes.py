from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from . import app
from app.services.auth_service import AuthService
from app.services.strategy_service import StrategyService
from app.services.simulation_service import SimulationService
from .models import User


@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    return jsonify(*AuthService.register(data))

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    return jsonify(*AuthService.login(data))

@app.route('/strategies', methods=['POST'])
@jwt_required()
def create_strategy():
    data = request.get_json()
    username = get_jwt_identity()
    response, status_code = StrategyService.create_strategy(data, username)
    return jsonify(response), status_code

@app.route('/strategies', methods=['GET'])
@jwt_required()
def get_strategies():
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    return jsonify(*StrategyService.get_strategies(user.id))

@app.route('/strategies/<int:id>', methods=['PUT'])
@jwt_required()
def update_strategy(id):
    data = request.get_json()
    username = get_jwt_identity()
    return jsonify(*StrategyService.update_strategy(id, data, username))

@app.route('/strategies/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_strategy(id):
    username = get_jwt_identity()
    return jsonify(*StrategyService.delete_strategy(id, username))

@app.route('/strategies/<int:id>/simulate', methods=['POST'])
@jwt_required()
def simulate_strategy(id):
    data = request.get_json()
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    return jsonify(*SimulationService.simulate_strategy(id, data, user.id))