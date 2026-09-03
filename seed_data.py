from app import app
from models import db, User, Item, Claim

with app.app_context():
    admin = User.query.filter_by(role="admin").first()

    if not admin:
        print("No admin user found. Register an account and run make_admin.py first.")
    else:
        bottle = Item(
            user_id=admin.id,
            item_type="Found",
            title="Blue Water Bottle",
            description="Blue stainless steel bottle, around 750ml. Left on a bench outside FCI.",
            category="Water Bottle",
            location="FCI",
            date_lost_found="2026-08-28",
            hidden_detail="Small dent near the base",
            status="Active",
        )

        umbrella = Item(
            user_id=admin.id,
            item_type="Lost",
            title="Black Umbrella",
            description="Plain black folding umbrella with a wooden handle.",
            category="Umbrella",
            location="Library",
            date_lost_found="2026-08-27",
            hidden_detail="Handle has a chip on one side",
            status="Active",
        )

        db.session.add(bottle)
        db.session.add(umbrella)
        db.session.commit()

        claim = Claim(
            item_id=bottle.id,
            claimant_id=admin.id,
            message="It has a dent near the bottom and a faded sticker on the side.",
            status="Pending",
        )
        db.session.add(claim)
        db.session.commit()

        print("Test data added: 2 items, 1 claim")