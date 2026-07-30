"""
=============================================================================
 CENTRAL FEATURE SWITCHBOARD
=============================================================================
Flip these booleans in code (not via any UI) to show/hide entire feature
areas across the whole app. This file is the single source of truth.

- advanced_admin:
    False -> Admin menu only exposes a bare "Add User" form (name, email,
             password). No user list, no edit/delete, no permission
             matrix, no audit log - those routes 404 even if the URL is
             typed directly.
    True  -> Full admin panel unlocks: user list, edit/delete, the
             per-module permission matrix, and the audit log.

- purchase_request / quotation / sales_order:
    False -> The module's nav link disappears AND every route in that
             module returns 404, so it's fully hidden, not just visually
             tucked away.
    True  -> Module behaves normally (still subject to each user's
             normal view/create/edit/delete permissions).

There is intentionally no admin-facing screen to change these values -
that's the point. Only someone with access to the codebase/deployment
can toggle them, which is why this lives in a plain Python module
instead of a database row.
=============================================================================
"""
from functools import wraps
from flask import abort

FEATURE_FLAGS = {
    "advanced_admin": False,
    "purchase_request": False,
    "quotation": False,
    "sales_order": False,
}


def feature_enabled(flag_name: str) -> bool:
    """Read-only check used by both templates and route guards."""
    return bool(FEATURE_FLAGS.get(flag_name, True))


def feature_required(flag_name: str):
    """Route decorator: 404s a view entirely when its feature flag is off.

    Place this ABOVE @login_required / @permission_required on a route so
    a disabled feature is invisible even to logged-out or admin traffic.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not feature_enabled(flag_name):
                abort(404)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator
