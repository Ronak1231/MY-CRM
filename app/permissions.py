"""
Central registry of feature modules covered by the permission system,
plus the decorator used across blueprints to enforce access control.

Every module supports 4 independent actions: view, create, edit, delete.
Admins (User.is_admin == True) implicitly have full access to everything.
Regular users only get what's explicitly granted via the Permission table,
which admins manage from the Admin > Users screen.
"""
from functools import wraps
from flask import abort
from flask_login import current_user

MODULES = [
    ("vendor", "Vendors"),
    ("product", "Products"),
    ("purchase_request", "Purchase Requests"),
    ("contact_purchase", "Purchase Contacts"),
    ("account", "Accounts"),
    ("contact_sales", "Sales Contacts"),
    ("lead", "Leads"),
    ("opportunity", "Opportunities"),
    ("quotation", "Quotations"),
    ("sales_order", "Sales Orders"),
    ("reports", "Reports"),
    ("user_management", "User Management"),
]

MODULE_KEYS = [m[0] for m in MODULES]
ACTIONS = ["view", "create", "edit", "delete"]

# Modules whose records carry an `owner_id` column and therefore participate
# in the owner-based data-visibility system below. ("reports" and
# "user_management" have no owner concept.)
OWNER_SCOPED_MODULES = [
    "vendor", "product", "contact_purchase", "account", "contact_sales",
    "lead", "opportunity", "quotation", "sales_order", "purchase_request",
]


def has_permission(user, module, action):
    """Return True if `user` may perform `action` on `module`."""
    if not user.is_authenticated:
        return False
    if user.is_admin:
        return True
    perm = next((p for p in user.permissions if p.module == module), None)
    if not perm:
        return False
    return bool(getattr(perm, f"can_{action}", False))


def can_view_all_owners(user, module):
    """True if `user` should see every owner's records for `module`
    (admins always can; otherwise it's an explicit per-module grant)."""
    if not user.is_authenticated:
        return False
    if user.is_admin:
        return True
    perm = next((p for p in user.permissions if p.module == module), None)
    return bool(perm and perm.can_view_all)


def visible_owner_ids(user, module):
    """
    Returns the set of owner_ids whose records `user` may see in `module`,
    or None if the user may see records from ALL owners (admin, or a user
    with the 'view all owners' grant for this module).

    Regular users always see at least their own records, plus anyone an
    admin has specifically granted access to via OwnerAccessGrant.
    """
    if can_view_all_owners(user, module):
        return None
    from app.models import OwnerAccessGrant

    ids = {user.id}
    grants = OwnerAccessGrant.query.filter_by(viewer_id=user.id, module=module).all()
    ids.update(g.owner_id for g in grants)
    return ids


def apply_owner_scope(query, model, user, module):
    """Filter a SQLAlchemy query on `model.owner_id` according to what
    `user` is allowed to see in `module`. No-op for admins / view-all users."""
    ids = visible_owner_ids(user, module)
    if ids is None:
        return query
    return query.filter(model.owner_id.in_(ids))


def can_view_record(user, module, owner_id):
    """Return True if `user` may view a single record owned by `owner_id`."""
    if not user.is_authenticated:
        return False
    ids = visible_owner_ids(user, module)
    if ids is None:
        return True
    return owner_id in ids


def permission_required(module, action):
    """View decorator: aborts with 403 if the current user lacks access."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not has_permission(current_user, module, action):
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator
