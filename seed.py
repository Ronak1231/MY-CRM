"""
Run this once to initialize the database:

    python seed.py

Creates all tables, a default admin login, and a small set of sample
records (vendor, product, account, lead, opportunity) so the app isn't
empty on first run. Safe to re-run - it skips creation if data already
exists.
"""
from datetime import date, timedelta
from app import create_app
from app.extensions import db
from app.models import (
    User, Vendor, Product, Account, Lead, Opportunity, ContactPerson, Lookup,
)

app = create_app()

with app.app_context():
    db.create_all()

    if not User.query.filter_by(email="admin@crm.com").first():
        admin = User(
            full_name="System Administrator",
            email="admin@crm.com",
            is_admin=True,
            is_active_user=True,
        )
        admin.set_password("Admin@123")
        db.session.add(admin)
        db.session.flush()
        print("Created default admin: admin@crm.com / Admin@123")
    else:
        admin = User.query.filter_by(email="admin@crm.com").first()
        print("Admin user already exists, skipping.")

    if Lookup.query.count() == 0:
        db.session.add_all([
            # Units
            Lookup(category="unit", value="pcs", label="Pieces", sort_order=1),
            Lookup(category="unit", value="box", label="Box", sort_order=2),
            Lookup(category="unit", value="kg", label="Kilogram", sort_order=3),
            Lookup(category="unit", value="ltr", label="Litre", sort_order=4),
            Lookup(category="unit", value="set", label="Set", sort_order=5),
            # Product categories
            Lookup(category="product_category", value="Electronics", sort_order=1),
            Lookup(category="product_category", value="Accessories", sort_order=2),
            Lookup(category="product_category", value="Software", sort_order=3),
            Lookup(category="product_category", value="Office Supplies", sort_order=4),
            # Payment terms
            Lookup(category="payment_terms", value="Net 15", sort_order=1),
            Lookup(category="payment_terms", value="Net 30", sort_order=2),
            Lookup(category="payment_terms", value="Net 45", sort_order=3),
            Lookup(category="payment_terms", value="Due on Receipt", sort_order=4),
            # Industries
            Lookup(category="industry", value="Software", sort_order=1),
            Lookup(category="industry", value="Manufacturing", sort_order=2),
            Lookup(category="industry", value="Retail", sort_order=3),
            Lookup(category="industry", value="Healthcare", sort_order=4),
            Lookup(category="industry", value="Finance", sort_order=5),
        ])
        print("Seeded default Lookup values (unit, product_category, payment_terms, industry).")

    if Vendor.query.count() == 0:
        vendor = Vendor(
            name="Acme Supplies Pvt Ltd",
            email="sales@acmesupplies.com",
            phone="+91-9876543210",
            city="Pune",
            country="India",
            gst_number="27AACCA1234F1Z5",
            payment_terms="Net 30",
            is_active=True,
            owner_id=admin.id,
        )
        db.session.add(vendor)
        db.session.flush()
        db.session.add(ContactPerson(
            contact_type="purchase", name="Rahul Sharma", designation="Sales Manager",
            email="rahul@acmesupplies.com", phone="+91-9876500001",
            is_primary=True, vendor_id=vendor.id, owner_id=admin.id,
        ))
        print("Created sample vendor: Acme Supplies Pvt Ltd")

    if Product.query.count() == 0:
        db.session.add_all([
            Product(sku="SKU-1001", name="Wireless Mouse", category="Electronics",
                     unit="pcs", cost_price=350, selling_price=599, stock_qty=120, reorder_level=20, owner_id=admin.id),
            Product(sku="SKU-1002", name="Mechanical Keyboard", category="Electronics",
                     unit="pcs", cost_price=1800, selling_price=2999, stock_qty=45, reorder_level=10, owner_id=admin.id),
            Product(sku="SKU-1003", name="USB-C Hub", category="Accessories",
                     unit="pcs", cost_price=650, selling_price=1199, stock_qty=80, reorder_level=15, owner_id=admin.id),
        ])
        print("Created 3 sample products.")

    if Account.query.count() == 0:
        account = Account(
            name="Nimbus Technologies", industry="Software", email="contact@nimbustech.com",
            phone="+91-9988776655", city="Bengaluru", country="India",
            website="https://nimbustech.com", is_active=True, owner_id=admin.id,
        )
        db.session.add(account)
        db.session.flush()
        db.session.add(ContactPerson(
            contact_type="sales", name="Priya Menon", designation="Procurement Head",
            email="priya@nimbustech.com", phone="+91-9988700002",
            is_primary=True, account_id=account.id, owner_id=admin.id,
        ))

        lead = Lead(
            name="Arjun Verma", company_name="BlueOrbit Retail", email="arjun@blueorbit.com",
            phone="+91-9900112233", source="Website", status="New", estimated_value=250000,
            owner_id=admin.id,
        )
        db.session.add(lead)

        opportunity = Opportunity(
            name="Nimbus Technologies - Q3 Hardware Deal", account_id=account.id,
            stage="Proposal", amount=180000, probability=60,
            expected_close_date=date.today() + timedelta(days=21),
            owner_id=admin.id,
        )
        db.session.add(opportunity)
        print("Created sample account, lead, and opportunity.")

    db.session.commit()
    print("\nDatabase ready. Start the app with:  python run.py")
