from . import db

class User(db.Model):
    """Моедель користувача."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Strategy(db.Model):
    """Модель торговой стратегії."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)
    buy_conditions = db.Column(db.JSON, nullable=False)
    sell_conditions = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('strategies', lazy=True))