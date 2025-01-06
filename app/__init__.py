from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from redis import Redis
import pika
import os
from dotenv import load_dotenv

# загрузка змінних з .env
load_dotenv()

# екземляр классу фласк
app = Flask(__name__)

# конфігурація
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['REDIS_HOST'] = 'localhost'

# init компонентів
db = SQLAlchemy(app)
jwt = JWTManager(app)
redis = Redis(host='localhost', port=6379, db=0)

# імпорт маршрутів
from . import routes
