from datetime import datetime
from app.extensions import db


def generate_number(model, field, prefix):
    """Generate a sequential document number like PR-000123 / SO-000045."""
    year = datetime.utcnow().strftime("%y")
    count = db.session.query(model).count() + 1
    return f"{prefix}-{year}{count:05d}"


def log_action(user, action, module, record_id=None):
    from app.models import AuditLog

    entry = AuditLog(
        user_id=user.id if user and user.is_authenticated else None,
        action=action,
        module=module,
        record_id=record_id,
    )
    db.session.add(entry)
    db.session.commit()


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_lookup_values(category):
    """Active Lookup entries for a category, in display order. Admins manage
    these from Admin > Lookups instead of them being hard-coded text fields."""
    from app.models import Lookup

    return (
        Lookup.query.filter_by(category=category, is_active=True)
        .order_by(Lookup.sort_order, Lookup.label, Lookup.value)
        .all()
    )


def get_active_users():
    """Active users, for 'Owner' dropdowns on record forms."""
    from app.models import User

    return User.query.filter_by(is_active_user=True).order_by(User.full_name).all()
