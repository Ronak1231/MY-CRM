# BizSuite — Vendor / Sales / CRM Management System

A production-structured Flask application covering the full purchase-to-cash
and lead-to-cash lifecycle, with an admin-managed, per-module RBAC system.

## Modules

**Purchase side**
- Vendors
- Products (shared catalog for both purchase & sales)
- Purchase Contacts (contact persons tied to a vendor)
- Purchase Requests (with line items, status workflow: Draft → Submitted →
  Approved → Ordered → Received)

**Sales / CRM side**
- Accounts (customers)
- Sales Contacts (contact persons tied to an account)
- Leads (with one-click "Convert" → creates an Account + Opportunity)
- Opportunities (stages incl. Won / Lost, with a dedicated close action and
  close-reason capture)
- Quotations (line items, one-click "Convert to Sales Order")
- Sales Orders (line items, auto-computed revenue / cost / profit)

**Reporting**
- All Sales (date-filterable, revenue/cost/profit totals)
- All Purchase (date-filterable, spend totals)
- Profit & Loss (gross profit, purchase spend, net profit, monthly breakdown)

**Admin**
- User creation with a per-user, per-module permission matrix
  (View / Create / Edit / Delete independently for every module)
- Admins have implicit full access; everyone else only sees what's granted
- Audit log of key actions (login, create/update/delete, permission changes)

## Feature toggle switchboard (`app/feature_flags.py`)

A few high-level areas can be switched on/off **only by editing code** —
there is no UI for this by design:

```python
FEATURE_FLAGS = {
    "advanced_admin": True,     # False -> only a bare "Add User" form is available
    "purchase_request": True,   # False -> Purchase Requests tab + routes disappear
    "quotation": True,          # False -> Quotations tab + routes disappear
    "sales_order": True,        # False -> Sales Orders tab + routes disappear
}
```

- When a module flag is `False`, its nav link is hidden **and** every route
  in that module returns `404`, even if someone types the URL directly.
- When `advanced_admin` is `False`, the Admin menu only exposes
  `/admin/users/quick-add` — a minimal form to create a user (name, email,
  password) with no permission assignment. The full user list, per-user
  permission matrix, edit/delete, and audit log all return `404` until you
  flip it back to `True` in code and restart the app.

To change any of this, edit the dict in `app/feature_flags.py` and restart
the app — that's the entire mechanism.

## Project layout

```
crm_erp/
├── app/
│   ├── __init__.py          # app factory, blueprint registration
│   ├── extensions.py        # db, login_manager, csrf
│   ├── models.py            # all SQLAlchemy models
│   ├── permissions.py       # MODULES registry + permission_required decorator
│   ├── feature_flags.py     # central on/off switchboard (see above)
│   ├── utils.py             # helpers (numbering, audit logging, casts)
│   ├── blueprints/
│   │   ├── auth.py
│   │   ├── admin.py
│   │   ├── dashboard.py
│   │   ├── vendor.py
│   │   ├── product.py
│   │   ├── purchase.py      # Purchase Requests
│   │   ├── contacts.py      # Purchase Contacts + Sales Contacts
│   │   ├── crm.py           # Accounts, Leads, Opportunities
│   │   ├── quotation.py
│   │   ├── sales.py         # Sales Orders
│   │   └── reports.py
│   ├── templates/           # Jinja2 + Bootstrap 5 UI
│   └── static/css/style.css
├── config.py
├── run.py
├── seed.py                  # creates tables + default admin + sample data
├── requirements.txt
└── README.md
```

## Getting started

```bash
python -m venv venv
source venv/bin/activate          # venv\Scripts\activate on Windows
pip install -r requirements.txt

python seed.py                    # creates the DB, admin user, sample data
python run.py                     # http://127.0.0.1:5000
```

Default admin login:

```
email:    admin@bizsuite.com
password: Admin@123
```

**Change this password immediately in any real deployment.**

## Permissions model

- `User.is_admin = True` → unrestricted access to everything, including the
  Admin panel itself.
- Everyone else has zero access by default. An admin grants access per
  module (`vendor`, `product`, `purchase_request`, `contact_purchase`,
  `account`, `contact_sales`, `lead`, `opportunity`, `quotation`,
  `sales_order`, `reports`, `user_management`) and per action
  (`view`, `create`, `edit`, `delete`) from **Admin → Users & Permissions**.
- The nav bar, action buttons, and the routes themselves all check the same
  `has_permission()` function, so hiding a button and blocking the route are
  never out of sync.

## Notes for a real production deployment

- Swap SQLite for Postgres/MySQL by changing `DATABASE_URL` in the
  environment (`config.py` already reads it).
- Add Flask-Migrate/Alembic for schema migrations instead of `db.create_all()`.
- Put this behind a real WSGI server (gunicorn/uWSGI) + reverse proxy;
  `run.py`'s built-in server is for development only.
- Set `SECRET_KEY` via environment variable, not the default in `config.py`.
- Enforce HTTPS (`SESSION_COOKIE_SECURE = True` is already set in
  `ProductionConfig`).

## Update: Owner field, data-visibility rules, and admin-editable lookups

This build adds three related features on top of the original CRM:

### 1. Owner field on every record
Accounts, Vendors, Products, Contacts, Purchase Requests, Quotations, and
Sales Orders (Leads/Opportunities already had this) now carry an `owner_id`.
New records default their owner to whoever creates them; every create/edit
form has an "Owner" dropdown so it can be reassigned to anyone.

### 2. Data visibility rules (who can see whose records)
- **Admins** always see everything, everywhere - unchanged.
- **Regular users** by default only see records they own.
- On **Admin > Users > Edit**, each module now has a "See all owners"
  checkbox - ticking it lets that user see *everyone's* records in that
  one module (like a mini-admin, scoped to just that tab).
- For finer control, **Admin > Users > Edit > Data Access** lets an admin
  pick, module by module, *exactly which other users'* records a given
  user is allowed to see - e.g. "Priya can see Rahul's leads and contacts,
  but nobody else's, and only in those two tabs."
- Trying to open a record you're not allowed to see (by direct URL) returns
  a 403, not just a hidden list row.

### 3. Admin-editable lookups (dropdowns instead of free text)
Product Unit & Category, Vendor Payment Terms, and Account Industry are now
backed by an admin-managed **Lookups** screen (Admin > Lookups) instead of
plain text boxes. Add, edit, reorder, or deactivate values there - no code
changes needed. The mechanism is generic, so more fields can be wired to a
new lookup category later the same way.

### Upgrading an existing database
If you already have data in `instance/crm_erp.db`, run the migration once:

```
python migrate_owner_lookups.py
```

It adds the new columns/tables via `ALTER TABLE` (nothing is dropped),
backfills `owner_id` on existing rows (defaulting to the first admin user,
or `created_by_id` where that already existed), and seeds a starter set of
Lookup values. It's safe to re-run.

Starting fresh instead? Just run `python seed.py` as before - it already
creates the new columns and starter Lookup values from scratch.
