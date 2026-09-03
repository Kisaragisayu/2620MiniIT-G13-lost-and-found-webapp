from app import app
from models import db, User

with app.app_context():
    user = User.query.filter_by(email="zhabaytemirlan@student.mmu.edu.my").first()
    if user:
        user.role = "admin"
        db.session.commit()
        print(f"{user.name} is now an admin")
    else:
        print("User not found")