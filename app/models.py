from datetime import datetime
from decimal import Decimal
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


def now():
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# AUTH / ADMIN
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active_user = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=now)

    permissions = db.relationship(
        "Permission", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # Flask-Login uses this to decide whether a session is valid
    @property
    def is_active(self):
        return self.is_active_user

    def permission_for(self, module):
        return next((p for p in self.permissions if p.module == module), None)

    def __repr__(self):
        return f"<User {self.email}>"


class Permission(db.Model):
    """Per-user, per-module CRUD permission grants set by an admin."""

    __tablename__ = "permissions"
    __table_args__ = (db.UniqueConstraint("user_id", "module", name="uq_user_module"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    can_view = db.Column(db.Boolean, default=False)
    can_create = db.Column(db.Boolean, default=False)
    can_edit = db.Column(db.Boolean, default=False)
    can_delete = db.Column(db.Boolean, default=False)
    can_view_all = db.Column(db.Boolean, default=False)

    user = db.relationship("User", back_populates="permissions")


class OwnerAccessGrant(db.Model):
    """Admin-set rule: viewer_id may see records owned by owner_id in module."""

    __tablename__ = "owner_access_grants"
    __table_args__ = (
        db.UniqueConstraint("viewer_id", "owner_id", "module", name="uq_viewer_owner_module"),
    )

    id = db.Column(db.Integer, primary_key=True)
    viewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=now)

    viewer = db.relationship("User", foreign_keys=[viewer_id])
    owner = db.relationship("User", foreign_keys=[owner_id])


class Lookup(db.Model):
    """Admin-manageable dropdown values, grouped by category (e.g. 'unit')."""

    __tablename__ = "lookups"
    __table_args__ = (db.UniqueConstraint("category", "value", name="uq_category_value"),)

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    value = db.Column(db.String(100), nullable=False)
    label = db.Column(db.String(120))
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now)

    @property
    def display_label(self):
        return self.label or self.value

    def __repr__(self):
        return f"<Lookup {self.category}:{self.value}>"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(255))
    module = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=now)

    user = db.relationship("User")


# ---------------------------------------------------------------------------
# PURCHASE SIDE
# ---------------------------------------------------------------------------
class Vendor(db.Model):
    __tablename__ = "vendors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    company_reg_no = db.Column(db.String(80))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    address = db.Column(db.String(255))
    city = db.Column(db.String(80))
    country = db.Column(db.String(80))
    gst_number = db.Column(db.String(50))
    payment_terms = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=now)

    owner = db.relationship("User", foreign_keys=[owner_id])
    contacts = db.relationship("ContactPerson", back_populates="vendor", cascade="all, delete-orphan")
    purchase_requests = db.relationship("PurchaseRequest", back_populates="vendor")

    def __repr__(self):
        return f"<Vendor {self.name}>"


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(60), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(80))
    unit = db.Column(db.String(30), default="pcs")
    cost_price = db.Column(db.Numeric(12, 2), default=0)
    selling_price = db.Column(db.Numeric(12, 2), default=0)
    stock_qty = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=now)

    owner = db.relationship("User", foreign_keys=[owner_id])

    def __repr__(self):
        return f"<Product {self.sku}>"


class ContactPerson(db.Model):
    """Contact person tied EITHER to a Vendor (purchase side) OR an Account (sales side)."""

    __tablename__ = "contact_persons"

    id = db.Column(db.Integer, primary_key=True)
    contact_type = db.Column(db.String(20), nullable=False)  # 'purchase' | 'sales'
    name = db.Column(db.String(120), nullable=False)
    designation = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    is_primary = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=now)

    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"))
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"))

    vendor = db.relationship("Vendor", back_populates="contacts")
    account = db.relationship("Account", back_populates="contacts")
    owner = db.relationship("User", foreign_keys=[owner_id])


PR_STATUS = ["Draft", "Submitted", "Approved", "Ordered", "Received", "Rejected", "Cancelled"]


class PurchaseRequest(db.Model):
    __tablename__ = "purchase_requests"

    id = db.Column(db.Integer, primary_key=True)
    pr_number = db.Column(db.String(30), unique=True, nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    contact_person_id = db.Column(db.Integer, db.ForeignKey("contact_persons.id"))
    status = db.Column(db.String(20), default="Draft")
    request_date = db.Column(db.Date, default=lambda: datetime.utcnow().date())
    expected_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=now)

    vendor = db.relationship("Vendor", back_populates="purchase_requests")
    contact_person = db.relationship("ContactPerson")
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    owner = db.relationship("User", foreign_keys=[owner_id])
    items = db.relationship("PurchaseRequestItem", back_populates="purchase_request", cascade="all, delete-orphan")

    @property
    def total_amount(self):
        return sum((item.quantity * item.unit_cost for item in self.items), 0)


class PurchaseRequestItem(db.Model):
    __tablename__ = "purchase_request_items"

    id = db.Column(db.Integer, primary_key=True)
    purchase_request_id = db.Column(db.Integer, db.ForeignKey("purchase_requests.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_cost = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    purchase_request = db.relationship("PurchaseRequest", back_populates="items")
    product = db.relationship("Product")

    @property
    def line_total(self):
        return Decimal(self.quantity or 0) * Decimal(self.unit_cost or 0)


# ---------------------------------------------------------------------------
# SALES / CRM SIDE
# ---------------------------------------------------------------------------
class Account(db.Model):
    """A customer / company account (sales side of the CRM)."""

    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    industry = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    address = db.Column(db.String(255))
    city = db.Column(db.String(80))
    country = db.Column(db.String(80))
    website = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=now)

    owner = db.relationship("User", foreign_keys=[owner_id])
    contacts = db.relationship("ContactPerson", back_populates="account", cascade="all, delete-orphan")
    leads = db.relationship("Lead", back_populates="account")
    opportunities = db.relationship("Opportunity", back_populates="account")
    quotations = db.relationship("Quotation", back_populates="account")
    sales_orders = db.relationship("SalesOrder", back_populates="account")

    def __repr__(self):
        return f"<Account {self.name}>"


LEAD_STATUS = ["New", "Contacted", "Qualified", "Unqualified", "Converted"]
LEAD_SOURCE = ["Website", "Referral", "Cold Call", "Advertisement", "Social Media", "Event", "Other"]


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    company_name = db.Column(db.String(150))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    source = db.Column(db.String(50), default="Other")
    status = db.Column(db.String(30), default="New")
    estimated_value = db.Column(db.Numeric(12, 2), default=0)
    notes = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"))
    created_at = db.Column(db.DateTime, default=now)

    owner = db.relationship("User")
    account = db.relationship("Account", back_populates="leads")

    def __repr__(self):
        return f"<Lead {self.name}>"


OPP_STAGES = [
    "Prospecting",
    "Qualification",
    "Proposal",
    "Negotiation",
    "Won",
    "Lost",
]


class Opportunity(db.Model):
    __tablename__ = "opportunities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"))
    stage = db.Column(db.String(30), default="Prospecting")
    amount = db.Column(db.Numeric(12, 2), default=0)
    probability = db.Column(db.Integer, default=10)  # % chance to close
    expected_close_date = db.Column(db.Date)
    close_reason = db.Column(db.String(255))  # why won / lost
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=now)

    account = db.relationship("Account", back_populates="opportunities")
    lead = db.relationship("Lead")
    owner = db.relationship("User")
    quotations = db.relationship("Quotation", back_populates="opportunity")

    @property
    def is_won(self):
        return self.stage == "Won"

    @property
    def is_lost(self):
        return self.stage == "Lost"

    def __repr__(self):
        return f"<Opportunity {self.name}>"


QUOTE_STATUS = ["Draft", "Sent", "Accepted", "Rejected", "Expired", "Converted"]


class Quotation(db.Model):
    __tablename__ = "quotations"

    id = db.Column(db.Integer, primary_key=True)
    quote_number = db.Column(db.String(30), unique=True, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    contact_person_id = db.Column(db.Integer, db.ForeignKey("contact_persons.id"))
    opportunity_id = db.Column(db.Integer, db.ForeignKey("opportunities.id"))
    status = db.Column(db.String(20), default="Draft")
    quote_date = db.Column(db.Date, default=lambda: datetime.utcnow().date())
    valid_until = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=now)

    account = db.relationship("Account", back_populates="quotations")
    contact_person = db.relationship("ContactPerson")
    opportunity = db.relationship("Opportunity", back_populates="quotations")
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    owner = db.relationship("User", foreign_keys=[owner_id])
    items = db.relationship("QuotationItem", back_populates="quotation", cascade="all, delete-orphan")
    sales_order = db.relationship("SalesOrder", back_populates="quotation", uselist=False)

    @property
    def total_amount(self):
        return sum((item.line_total for item in self.items), 0)


class QuotationItem(db.Model):
    __tablename__ = "quotation_items"

    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey("quotations.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    discount_pct = db.Column(db.Numeric(5, 2), default=0)

    quotation = db.relationship("Quotation", back_populates="items")
    product = db.relationship("Product")

    @property
    def line_total(self):
        gross = Decimal(self.quantity or 0) * Decimal(self.unit_price or 0)
        discount = gross * (Decimal(self.discount_pct or 0) / Decimal(100))
        return gross - discount


SO_STATUS = ["Pending", "Confirmed", "Shipped", "Delivered", "Invoiced", "Cancelled"]


class SalesOrder(db.Model):
    __tablename__ = "sales_orders"

    id = db.Column(db.Integer, primary_key=True)
    so_number = db.Column(db.String(30), unique=True, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    contact_person_id = db.Column(db.Integer, db.ForeignKey("contact_persons.id"))
    quotation_id = db.Column(db.Integer, db.ForeignKey("quotations.id"))
    status = db.Column(db.String(20), default="Pending")
    order_date = db.Column(db.Date, default=lambda: datetime.utcnow().date())
    delivery_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=now)

    account = db.relationship("Account", back_populates="sales_orders")
    contact_person = db.relationship("ContactPerson")
    quotation = db.relationship("Quotation", back_populates="sales_order")
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    owner = db.relationship("User", foreign_keys=[owner_id])
    items = db.relationship("SalesOrderItem", back_populates="sales_order", cascade="all, delete-orphan")

    @property
    def total_amount(self):
        return sum((item.line_total for item in self.items), 0)

    @property
    def total_cost(self):
        total = 0
        for item in self.items:
            cost = item.product.cost_price if item.product else 0
            total += (item.quantity or 0) * (cost or 0)
        return total

    @property
    def profit(self):
        return self.total_amount - self.total_cost


class SalesOrderItem(db.Model):
    __tablename__ = "sales_order_items"

    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey("sales_orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    discount_pct = db.Column(db.Numeric(5, 2), default=0)

    sales_order = db.relationship("SalesOrder", back_populates="items")
    product = db.relationship("Product")

    @property
    def line_total(self):
        gross = Decimal(self.quantity or 0) * Decimal(self.unit_price or 0)
        discount = gross * (Decimal(self.discount_pct or 0) / Decimal(100))
        return gross - discount