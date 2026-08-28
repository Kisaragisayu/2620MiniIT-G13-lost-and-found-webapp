from flask import Flask
from models import db

app = Flask(__name__)
app.config["SECRET_KEY"] = "Lost&found2620"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lostfound.db"

db.init_app(app)

@app.route("/")
def home():
    return "Database connected!"

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)