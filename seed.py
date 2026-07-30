"""
Run this once to initialize the database:

    python seed.py

Creates all tables, a default admin login, and a richer set of sample
records (vendors, products, accounts, leads, opportunities) so the app
isn't empty on first run. Safe to re-run - it skips creation if data
already exists.
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
            Lookup(category="product_category", value="Furniture", sort_order=5),
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
            Lookup(category="industry", value="Education", sort_order=6),
            Lookup(category="industry", value="Logistics", sort_order=7),
        ])
        print("Seeded default Lookup values (unit, product_category, payment_terms, industry).")

    # ------------------------------------------------------------------
    # Vendors
    # ------------------------------------------------------------------
    if Vendor.query.count() == 0:
        vendors_data = [
            dict(
                name="Acme Supplies Pvt Ltd", email="sales@acmesupplies.com",
                phone="+91-9876543210", city="Pune", country="India",
                gst_number="27AACCA1234F1Z5", payment_terms="Net 30",
                contact=dict(name="Rahul Sharma", designation="Sales Manager",
                             email="rahul@acmesupplies.com", phone="+91-9876500001"),
            ),
            dict(
                name="Bluewave Electronics", email="orders@bluewaveelec.com",
                phone="+91-8765432109", city="Mumbai", country="India",
                gst_number="27AABCB5678G1Z2", payment_terms="Net 45",
                contact=dict(name="Sneha Kulkarni", designation="Account Executive",
                             email="sneha@bluewaveelec.com", phone="+91-8765400002"),
            ),
            dict(
                name="Global Office Traders", email="info@globalofficetraders.com",
                phone="+91-7654321098", city="Delhi", country="India",
                gst_number="07AAACG4321H1Z9", payment_terms="Due on Receipt",
                contact=dict(name="Manish Gupta", designation="Regional Head",
                             email="manish@globalofficetraders.com", phone="+91-7654300003"),
            ),
        ]
        for v in vendors_data:
            contact_info = v.pop("contact")
            vendor = Vendor(is_active=True, owner_id=admin.id, **v)
            db.session.add(vendor)
            db.session.flush()
            db.session.add(ContactPerson(
                contact_type="purchase", is_primary=True,
                vendor_id=vendor.id, owner_id=admin.id, **contact_info,
            ))
        print(f"Created {len(vendors_data)} sample vendors with contacts.")

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------
    if Product.query.count() == 0:
        db.session.add_all([
            Product(sku="SKU-1001", name="Wireless Mouse", category="Electronics",
                     unit="pcs", cost_price=350, selling_price=599, stock_qty=120, reorder_level=20, owner_id=admin.id),
            Product(sku="SKU-1002", name="Mechanical Keyboard", category="Electronics",
                     unit="pcs", cost_price=1800, selling_price=2999, stock_qty=45, reorder_level=10, owner_id=admin.id),
            Product(sku="SKU-1003", name="USB-C Hub", category="Accessories",
                     unit="pcs", cost_price=650, selling_price=1199, stock_qty=80, reorder_level=15, owner_id=admin.id),
            Product(sku="SKU-1004", name="27-inch 4K Monitor", category="Electronics",
                     unit="pcs", cost_price=15500, selling_price=21999, stock_qty=25, reorder_level=5, owner_id=admin.id),
            Product(sku="SKU-1005", name="Laptop Stand", category="Accessories",
                     unit="pcs", cost_price=420, selling_price=799, stock_qty=150, reorder_level=25, owner_id=admin.id),
            Product(sku="SKU-1006", name="CRM Pro License (Annual)", category="Software",
                     unit="set", cost_price=0, selling_price=24999, stock_qty=999, reorder_level=0, owner_id=admin.id),
            Product(sku="SKU-1007", name="A4 Copier Paper (Ream)", category="Office Supplies",
                     unit="box", cost_price=220, selling_price=349, stock_qty=300, reorder_level=50, owner_id=admin.id),
            Product(sku="SKU-1008", name="Ergonomic Office Chair", category="Furniture",
                     unit="pcs", cost_price=6200, selling_price=9499, stock_qty=18, reorder_level=5, owner_id=admin.id),
            Product(sku="SKU-1009", name="Standing Desk", category="Furniture",
                     unit="pcs", cost_price=11500, selling_price=16999, stock_qty=10, reorder_level=3, owner_id=admin.id),
            Product(sku="SKU-1010", name="Noise-Cancelling Headset", category="Electronics",
                     unit="pcs", cost_price=2800, selling_price=4499, stock_qty=60, reorder_level=10, owner_id=admin.id),
        ])
        print("Created 10 sample products.")

    # ------------------------------------------------------------------
    # Accounts (+ contacts)
    # ------------------------------------------------------------------
    if Account.query.count() == 0:
        accounts_data = [
            dict(
                name="Nimbus Technologies", industry="Software", email="contact@nimbustech.com",
                phone="+91-9988776655", city="Bengaluru", country="India", website="https://nimbustech.com",
                contact=dict(name="Priya Menon", designation="Procurement Head",
                             email="priya@nimbustech.com", phone="+91-9988700002"),
            ),
            dict(
                name="Harborline Logistics", industry="Logistics", email="hello@harborline.com",
                phone="+91-9123456780", city="Chennai", country="India", website="https://harborline.com",
                contact=dict(name="Karthik Iyer", designation="Operations Director",
                             email="karthik@harborline.com", phone="+91-9123400001"),
            ),
            dict(
                name="Meridian Healthcare Group", industry="Healthcare", email="admin@meridianhealth.in",
                phone="+91-9345678901", city="Hyderabad", country="India", website="https://meridianhealth.in",
                contact=dict(name="Dr. Anjali Rao", designation="Chief Administrator",
                             email="anjali.rao@meridianhealth.in", phone="+91-9345600002"),
            ),
            dict(
                name="Fintrust Capital Advisors", industry="Finance", email="info@fintrustcapital.com",
                phone="+91-9871234560", city="Mumbai", country="India", website="https://fintrustcapital.com",
                contact=dict(name="Rohan Desai", designation="VP Operations",
                             email="rohan@fintrustcapital.com", phone="+91-9871200003"),
            ),
        ]
        created_accounts = []
        for a in accounts_data:
            contact_info = a.pop("contact")
            account = Account(is_active=True, owner_id=admin.id, **a)
            db.session.add(account)
            db.session.flush()
            db.session.add(ContactPerson(
                contact_type="sales", is_primary=True,
                account_id=account.id, owner_id=admin.id, **contact_info,
            ))
            created_accounts.append(account)
        print(f"Created {len(accounts_data)} sample accounts with contacts.")

        # ------------------------------------------------------------------
        # Leads
        # ------------------------------------------------------------------
        db.session.add_all([
            Lead(name="Arjun Verma", company_name="BlueOrbit Retail", email="arjun@blueorbit.com",
                 phone="+91-9900112233", source="Website", status="New", estimated_value=250000,
                 owner_id=admin.id),
            Lead(name="Neha Kapoor", company_name="Silverline Manufacturing", email="neha@silverlinemfg.com",
                 phone="+91-9811223344", source="Referral", status="Contacted", estimated_value=480000,
                 owner_id=admin.id),
            Lead(name="Farhan Sheikh", company_name="Coastal Foods Ltd", email="farhan@coastalfoods.com",
                 phone="+91-9822334455", source="Trade Show", status="Qualified", estimated_value=125000,
                 owner_id=admin.id),
            Lead(name="Divya Nair", company_name="Zenith Software Labs", email="divya@zenithlabs.io",
                 phone="+91-9833445566", source="Cold Call", status="New", estimated_value=95000,
                 owner_id=admin.id),
            Lead(name="Vikram Oberoi", company_name="Oberoi Textiles", email="vikram@oberoitextiles.com",
                 phone="+91-9844556677", source="Website", status="Unqualified", estimated_value=60000,
                 owner_id=admin.id),
        ])
        print("Created 5 sample leads.")

        # ------------------------------------------------------------------
        # Opportunities
        # ------------------------------------------------------------------
        db.session.add_all([
            Opportunity(name="Nimbus Technologies - Q3 Hardware Deal", account_id=created_accounts[0].id,
                        stage="Proposal", amount=180000, probability=60,
                        expected_close_date=date.today() + timedelta(days=21), owner_id=admin.id),
            Opportunity(name="Harborline - Fleet Tracking Software", account_id=created_accounts[1].id,
                        stage="Negotiation", amount=320000, probability=75,
                        expected_close_date=date.today() + timedelta(days=14), owner_id=admin.id),
            Opportunity(name="Meridian Healthcare - Office Furniture Rollout", account_id=created_accounts[2].id,
                        stage="Qualification", amount=540000, probability=40,
                        expected_close_date=date.today() + timedelta(days=45), owner_id=admin.id),
            Opportunity(name="Fintrust Capital - CRM Licensing", account_id=created_accounts[3].id,
                        stage="Closed Won", amount=99999, probability=100,
                        expected_close_date=date.today() - timedelta(days=5), owner_id=admin.id),
            Opportunity(name="Nimbus Technologies - Annual Support Renewal", account_id=created_accounts[0].id,
                        stage="Prospecting", amount=75000, probability=20,
                        expected_close_date=date.today() + timedelta(days=60), owner_id=admin.id),
        ])
        print("Created 5 sample opportunities across various stages.")

    db.session.commit()
    print("\nDatabase ready. Start the app with:  python run.py")