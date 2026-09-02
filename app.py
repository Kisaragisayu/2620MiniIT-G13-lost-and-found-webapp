from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

app = Flask(__name__)
app.config["SECRET_KEY"] = "Lost&found2620"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lostfound.db"

db.init_app(app)

@app.route("/")
def home():
    return "Home page (placeholder for now)"

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not email.endswith("@student.mmu.edu.my") and not email.endswith("@mmu.edu.my"):
            flash("Registration is only open to MMU emails.")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.")
            return redirect(url_for("register"))

        new_user = User(name=name, email=email, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        flash("Account created! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            flash(f"Welcome back, {user.name}!")
            return redirect(url_for("home"))

        flash("Incorrect email or password.")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
