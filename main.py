from app import app
from app.models import db


# функція для створення таблиць в бд ()
def create_tables():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    create_tables()
    app.run(debug=True, port=5001)
