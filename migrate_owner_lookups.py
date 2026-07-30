"""
One-time migration for EXISTING installs (databases created before the
owner-field / data-visibility / lookup features were added).

Safe to run multiple times - every step checks first and skips if already
applied. Run it once after pulling this update:

    python migrate_owner_lookups.py

What it does:
  1. Adds `owner_id` to accounts, vendors, products, contact_persons,
     purchase_requests, quotations, sales_orders (nullable, via ALTER TABLE).
  2. Adds `can_view_all` to permissions.
  3. Creates the new `owner_access_grants` and `lookups` tables.
  4. Backfills owner_id on existing rows:
       - accounts/vendors/products/contacts: no natural creator column, so
         they're assigned to the first admin user.
       - purchase_requests/quotations/sales_orders: owner_id = created_by_id
         (falls back to the first admin if created_by_id is empty).
  5. Seeds a starter set of Lookup values if the table is empty.

If you'd rather start fresh (e.g. this is a dev/demo database), it's
simpler to just delete instance/crm_erp.db and run `python seed.py` instead
- that already creates everything with the new columns from scratch.
"""
import sqlalchemy as sa
from app import create_app
from app.extensions import db
from app.models import User, Lookup

app = create_app()

TABLES_NEEDING_OWNER = [
    "accounts", "vendors", "products", "contact_persons",
    "purchase_requests", "quotations", "sales_orders",
]


def column_exists(table, column):
    inspector = sa.inspect(db.engine)
    return column in [c["name"] for c in inspector.get_columns(table)]


def table_exists(table):
    return sa.inspect(db.engine).has_table(table)


with app.app_context():
    with db.engine.begin() as conn:
        # 1. owner_id on each owner-scoped table
        for table in TABLES_NEEDING_OWNER:
            if not column_exists(table, "owner_id"):
                conn.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN owner_id INTEGER"))
                print(f"Added owner_id to {table}")
            else:
                print(f"{table}.owner_id already present, skipping")

        # 2. can_view_all on permissions
        if table_exists("permissions") and not column_exists("permissions", "can_view_all"):
            conn.execute(sa.text("ALTER TABLE permissions ADD COLUMN can_view_all BOOLEAN DEFAULT 0"))
            print("Added permissions.can_view_all")
        else:
            print("permissions.can_view_all already present (or table missing), skipping")

    # 3. New tables (owner_access_grants, lookups) - safe no-op if they exist
    db.create_all()
    print("Ensured owner_access_grants / lookups tables exist.")

    # 4. Backfill owner_id on existing rows
    admin = User.query.filter_by(is_admin=True).order_by(User.id).first()
    if admin:
        with db.engine.begin() as conn:
            for table in ["accounts", "vendors", "products", "contact_persons"]:
                conn.execute(sa.text(
                    f"UPDATE {table} SET owner_id = :aid WHERE owner_id IS NULL"
                ), {"aid": admin.id})
            for table in ["purchase_requests", "quotations", "sales_orders"]:
                conn.execute(sa.text(
                    f"UPDATE {table} SET owner_id = COALESCE(created_by_id, :aid) WHERE owner_id IS NULL"
                ), {"aid": admin.id})
            # leads/opportunities already had an owner_id column before this
            # upgrade, but older rows (e.g. from an earlier seed.py) may
            # still have it NULL - fix those up too so they aren't
            # invisible to non-admins.
            for table in ["leads", "opportunities"]:
                if table_exists(table):
                    conn.execute(sa.text(
                        f"UPDATE {table} SET owner_id = :aid WHERE owner_id IS NULL"
                    ), {"aid": admin.id})
        print(f"Backfilled owner_id on existing records (default owner: {admin.email}).")
    else:
        print("No admin user found yet - skipping owner_id backfill. Run seed.py first, or set owners manually.")

    # 5. Seed starter lookup values if none exist
    if Lookup.query.count() == 0:
        db.session.add_all([
            Lookup(category="unit", value="pcs", label="Pieces", sort_order=1),
            Lookup(category="unit", value="box", label="Box", sort_order=2),
            Lookup(category="unit", value="kg", label="Kilogram", sort_order=3),
            Lookup(category="unit", value="ltr", label="Litre", sort_order=4),
            Lookup(category="unit", value="set", label="Set", sort_order=5),
            Lookup(category="product_category", value="Electronics", sort_order=1),
            Lookup(category="product_category", value="Accessories", sort_order=2),
            Lookup(category="product_category", value="Software", sort_order=3),
            Lookup(category="product_category", value="Office Supplies", sort_order=4),
            Lookup(category="payment_terms", value="Net 15", sort_order=1),
            Lookup(category="payment_terms", value="Net 30", sort_order=2),
            Lookup(category="payment_terms", value="Net 45", sort_order=3),
            Lookup(category="payment_terms", value="Due on Receipt", sort_order=4),
            Lookup(category="industry", value="Software", sort_order=1),
            Lookup(category="industry", value="Manufacturing", sort_order=2),
            Lookup(category="industry", value="Retail", sort_order=3),
            Lookup(category="industry", value="Healthcare", sort_order=4),
            Lookup(category="industry", value="Finance", sort_order=5),
        ])
        db.session.commit()
        print("Seeded default Lookup values.")
    else:
        print("Lookup values already present, skipping seed.")

    print("\nMigration complete.")
