from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token

from .. import db
from ..models import User
from flask import jsonify

class AuthService:
    @staticmethod
    def register(data):
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify(message="Username and password are required"), 400

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify(message="Username already exists"), 400

        hashed_password = generate_password_hash(password)

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return jsonify(message="User registered successfully"), 201

    @staticmethod
    def login(data):
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