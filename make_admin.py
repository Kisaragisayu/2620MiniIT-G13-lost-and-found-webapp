import sys
from app import app
from models import db, User

email = sys.argv[1] if len(sys.argv) > 1 else None
if not email:
    print("Usage: python make_admin.py your@student.mmu.edu.my")
    sys.exit(1)

with app.app_context():
    user = User.query.filter_by(email=email.strip().lower()).first()
    if user:
        user.role = "superadmin"
        db.session.commit()
        print(f"{user.name} is now the super admin")
    else:
        print("User not found")