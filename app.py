import os
from datetime import date
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort 
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge


from models import db, User, Item, Claim, Flag

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-local-only")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lostfound.db"
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)

LOCATIONS = ["FCI", "FOE", "FCM", "Library", "Arked", "Bus Stop", "Hostel Block", "Sports Complex", "Other"]
CATEGORIES = ["Student ID / Matric Card", "Wallet", "Phone", "Charger / Cable", "Water Bottle", "Umbrella", "Bag", "Keys", "Other"]
SECURITY_QUESTIONS = [                                    
    "What was the name of your first school?",
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "What city were you born in?",
    "Other"
]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def current_user():
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        if user and user.is_banned:
            session.pop("user_id", None)
            return None
        return user
    return None

ADMIN_ROLES = ("admin", "superadmin")


def require_admin():
    user = current_user()
    return user if user and user.role in ADMIN_ROLES else None


def require_superadmin():
    user = current_user()
    return user if user and user.role == "superadmin" else None


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    user = current_user()

    # Claims waiting on this user's own listings. Without a count in the navbar
    # the author only finds out someone claimed their item by opening the
    # listing and checking, which can take days on a service meant to return
    # property quickly. Claims the user has made themselves are a different
    # thing — those wait on somebody else — so they are not counted here.
    pending_claims = 0
    if user:
        pending_claims = (
            Claim.query
            .join(Item, Claim.item_id == Item.id)
            .filter(Item.user_id == user.id, Claim.status == "Pending")
            .count()
        )

    return {"current_user": user, "pending_claims": pending_claims}


@app.route("/")
def home():
    query = Item.query.filter(Item.status == "Active")

    keyword = request.args.get("keyword", "").strip()
    category = request.args.get("category", "")
    location = request.args.get("location", "")

    if keyword:
        query = query.filter(Item.title.ilike(f"%{keyword}%") | Item.description.ilike(f"%{keyword}%"))
    if category:
        query = query.filter(Item.category == category)
    if location:
        query = query.filter(Item.location == location)

    items = query.order_by(Item.created_at.desc()).all()
    return render_template("index.html", items=items, categories=CATEGORIES,
                           locations=LOCATIONS, selected_category=category,
                           selected_location=location, keyword=keyword)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        security_question = request.form.get("security_question")
        security_answer = request.form.get("security_answer", "").strip().lower()

        if not email.endswith("@student.mmu.edu.my") and not email.endswith("@mmu.edu.my"):
            flash("Registration is only open to MMU emails.", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return redirect(url_for("register"))

        new_user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            security_question=security_question,
            security_answer_hash=generate_password_hash(security_answer),
        )       
        db.session.add(new_user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", questions=SECURITY_QUESTIONS)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            if user.is_banned:
                flash("This account has been suspended.", "error")
                return redirect(url_for("login"))
            session["user_id"] = user.id
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(url_for("home"))

        flash("Incorrect email or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/admin")
def admin_panel():
    user = require_admin()
    if not user:
        abort(403) 


    users = User.query.all()
    items = Item.query.all()
    claims = Claim.query.all()
    flags = Flag.query.order_by(Flag.created_at.desc()).all()

    # Counted from the lists already fetched rather than with five more queries.
    # The four tabs show every row there is; what an admin actually needs to know
    # on arrival is how much is waiting on them, which is what these summarise.
    stats = {
        "active_items": sum(1 for i in items if i.status == "Active"),
        "resolved_items": sum(1 for i in items if i.status != "Active"),
        "pending_claims": sum(1 for c in claims if c.status == "Pending"),
        "open_flags": sum(1 for f in flags if f.status == "Open"),
        "banned_users": sum(1 for u in users if u.is_banned),
    }

    return render_template(
        "admin.html",
        users=users,
        items=items,
        claims=claims,
        flags=flags,
        stats=stats,
    )


@app.route("/admin/item/<int:item_id>/remove", methods=["POST"])
def admin_remove_item(item_id):
    user = require_admin()
    if not user:
        abort(403)

    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash(f"Listing '{item.title}' has been removed.", "success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/user/<int:user_id>/role", methods=["POST"])
def admin_toggle_role(user_id):
    actor = require_superadmin()
    if not actor:
        abort(403) 

    target = User.query.get_or_404(user_id)

    if target.id == actor.id:
        flash("You cannot change your own role.", "error")
        return redirect(url_for("admin_panel"))

    if target.role == "superadmin":
        flash("The super admin's role cannot be changed here.", "error")
        return redirect(url_for("admin_panel"))

    if target.role == "admin":
        target.role = "user"
        flash(f"{target.name} is no longer an admin.", "success")
    else:
        if target.is_banned:
            flash("Unban this account before making it an admin.", "error")
            return redirect(url_for("admin_panel"))
        target.role = "admin"
        flash(f"{target.name} is now an admin.", "success")

    db.session.commit()
    return redirect(url_for("admin_panel"))


@app.route("/item/<int:item_id>/flag", methods=["POST"])
@login_required
def flag_item(item_id):
    item = Item.query.get_or_404(item_id)

    existing = Flag.query.filter_by(item_id=item.id, reporter_id=session["user_id"]).first()
    if existing:
        flash("You have already reported this listing.", "error")
        return redirect(url_for("home"))

    new_flag = Flag(
        item_id=item.id,
        reporter_id=session["user_id"],
        reason=request.form["reason"].strip(),
    )
    db.session.add(new_flag)
    db.session.commit()
    flash("Thank you. This listing has been reported for review.", "success")
    return redirect(url_for("home"))


@app.route("/admin/flag/<int:flag_id>/review", methods=["POST"])
def admin_review_flag(flag_id):
    user = require_admin()
    if not user:
        abort(403)

    flag = Flag.query.get_or_404(flag_id)
    flag.status = "Reviewed"
    db.session.commit()
    flash("Flag marked as reviewed.", "success")
    return redirect(url_for("admin_panel"))

@app.route("/post", methods=["GET", "POST"])
@login_required
def post_item():
    if request.method == "POST":
        date_lost_found = request.form["date_lost_found"]

        if date_lost_found > date.today().isoformat():
            flash("Date lost/found cannot be in the future.", "error")
            return redirect(url_for("post_item"))

        image_filename = None
        file = request.files.get("photo")
        if file and file.filename:
            # Skipping the file silently left the listing posted with no photo
            # and nothing said about it, which reads as the upload having worked.
            if not allowed_file(file.filename):
                flash("That image format isn't supported. Use PNG, JPG, GIF or WEBP.", "error")
                return redirect(url_for("post_item"))
            image_filename = secure_filename(f"{session['user_id']}_{file.filename}")
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))

        new_item = Item(
            user_id=session["user_id"],
            item_type=request.form["item_type"],
            title=request.form["title"].strip(),
            description=request.form["description"].strip(),
            category=request.form["category"],
            location=request.form["location"],
            date_lost_found=date_lost_found,
            hidden_detail=request.form["hidden_detail"].strip(),
            image_filename=image_filename,
            status="Active",
        )
        db.session.add(new_item)
        db.session.commit()
        flash("Your item has been posted.", "success")
        return redirect(url_for("item_detail", item_id=new_item.id))

    return render_template("post-item.html", categories=CATEGORIES, locations=LOCATIONS)



@app.route("/item/<int:item_id>")
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    user = current_user()
    claims = item.claims if user and user.id == item.user_id else []
    return render_template("item-detail.html", item=item, claims=claims)

@app.route("/item/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.user_id != session["user_id"]:
        flash("You can only edit your own listings.", "error")
        return redirect(url_for("item_detail", item_id=item.id))

    if request.method == "POST":
        item.title = request.form["title"].strip()
        item.description = request.form["description"].strip()
        item.category = request.form["category"]
        item.location = request.form["location"]
        item.hidden_detail = request.form["hidden_detail"].strip()
        db.session.commit()
        flash("Listing updated.", "success")
        return redirect(url_for("item_detail", item_id=item.id))

    return render_template("post-item.html", item=item, categories=CATEGORIES,
                           locations=LOCATIONS, editing=True)


@app.route("/item/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.user_id != session["user_id"]:
        flash("You can only delete your own listings.", "error")
        return redirect(url_for("item_detail", item_id=item.id))
    db.session.delete(item)
    db.session.commit()
    flash("Listing deleted.", "success")
    return redirect(url_for("home"))


@app.route("/item/<int:item_id>/resolve", methods=["POST"])
@login_required
def resolve_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.user_id != session["user_id"]:
        flash("You can only update your own listings.", "error")
        return redirect(url_for("item_detail", item_id=item.id))
    item.status = "Resolved"
    db.session.commit()
    flash("Marked as resolved.", "success")
    return redirect(url_for("item_detail", item_id=item.id))


@app.route("/admin/user/<int:user_id>/ban", methods=["POST"])
def admin_ban_user(user_id):
    admin = require_admin()
    if not admin:
        abort(403)

    target = User.query.get_or_404(user_id)

    if target.role in ADMIN_ROLES:
        flash("Admin accounts cannot be banned.", "error")
        return redirect(url_for("admin_panel"))

    target.is_banned = not target.is_banned
    db.session.commit()

    if target.is_banned:
        flash(f"{target.name} has been banned.", "success")
    else:
        flash(f"{target.name} has been unbanned.", "success")

    return redirect(url_for("admin_panel"))


@app.route("/item/<int:item_id>/claim", methods=["POST"])
@login_required
def submit_claim(item_id):
    item = Item.query.get_or_404(item_id)

    if item.user_id == session["user_id"]:
        flash("You can't claim your own listing.", "error")
        return redirect(url_for("item_detail", item_id=item.id))
    if item.status != "Active":
        flash("This item is no longer active.", "error")
        return redirect(url_for("item_detail", item_id=item.id))

    existing = Claim.query.filter_by(item_id=item.id, claimant_id=session["user_id"]).first()
    if existing:
        flash("You have already submitted a claim on this listing.", "error")
        return redirect(url_for("item_detail", item_id=item.id))

    new_claim = Claim(
        item_id=item.id,
        claimant_id=session["user_id"],
        message=request.form["message"].strip(),
    )
    db.session.add(new_claim)
    db.session.commit()
    flash("Your claim has been submitted. The reporter will review it.", "success")
    return redirect(url_for("item_detail", item_id=item.id))


@app.route("/claim/<int:claim_id>/approve", methods=["POST"])
@login_required
def approve_claim(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    item = claim.item

    if item.user_id != session["user_id"]:
        flash("Only the reporter can approve claims.", "error")
        return redirect(url_for("item_detail", item_id=item.id))

    claim.status = "Approved"
    for other in item.claims:
        if other.id != claim.id and other.status == "Pending":
            other.status = "Closed"

    item.status = "Resolved"
    db.session.commit()
    flash(f"Claim approved. Contact {claim.claimant.name} ({claim.claimant.email}) to arrange handover.", "success")
    return redirect(url_for("item_detail", item_id=item.id))


@app.route("/claim/<int:claim_id>/reject", methods=["POST"])
@login_required
def reject_claim(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    item = claim.item

    if item.user_id != session["user_id"]:
        flash("Only the reporter can reject claims.", "error")
        return redirect(url_for("item_detail", item_id=item.id))

    claim.status = "Rejected"
    db.session.commit()
    flash("Claim rejected.", "success")
    return redirect(url_for("item_detail", item_id=item.id))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user or not user.security_question:
            flash("No account found with that email.", "error")
            return redirect(url_for("forgot_password"))

        session["reset_email"] = user.email
        return redirect(url_for("reset_password"))

    return render_template("forgot-password.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = session.get("reset_email")
    if not email:
        flash("Start the password reset from the beginning.", "error")
        return redirect(url_for("forgot_password"))

    user = User.query.filter_by(email=email).first()
    if not user:
        session.pop("reset_email", None)
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        answer = request.form["security_answer"].strip().lower()
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if not check_password_hash(user.security_answer_hash, answer):
            flash("Incorrect answer.", "error")
            return redirect(url_for("reset_password"))

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("reset_password"))

        user.password_hash = generate_password_hash(password)
        db.session.commit()
        session.pop("reset_email", None)
        flash("Password updated. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("reset-password.html", question=user.security_question)

@app.route("/profile")
@login_required
def profile():
    user = current_user()
    my_items = Item.query.filter_by(user_id=user.id).order_by(Item.created_at.desc()).all()
    my_claims = Claim.query.filter_by(claimant_id=user.id).order_by(Claim.created_at.desc()).all()
    return render_template("profile.html", my_items=my_items, my_claims=my_claims)


@app.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    user = current_user()
    current = request.form["current_password"]
    new = request.form["new_password"]
    confirm = request.form["confirm_password"]

    if not check_password_hash(user.password_hash, current):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("profile"))
    if new != confirm:
        flash("New passwords do not match.", "error")
        return redirect(url_for("profile"))

    user.password_hash = generate_password_hash(new)
    db.session.commit()
    flash("Password updated.", "success")
    return redirect(url_for("profile"))

@app.errorhandler(RequestEntityTooLarge)
def file_too_large(e):
    flash("That photo is too large. Maximum size is 2 MB.", "error")
    return redirect(url_for("post_item"))

@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.route("/profile/name", methods=["POST"])
@login_required
def change_name():
    user = current_user()
    new_name = request.form["name"].strip()

    if not new_name:
        flash("Name cannot be empty.", "error")
        return redirect(url_for("profile"))

    user.name = new_name
    db.session.commit()
    flash("Name updated.", "success")
    return redirect(url_for("profile"))

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run()