from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import User, Permission, AuditLog, OwnerAccessGrant, Lookup
from app.permissions import MODULES, ACTIONS, OWNER_SCOPED_MODULES
from app.utils import log_action
from app.feature_flags import feature_required

admin_bp = Blueprint("admin", __name__)


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped


@admin_bp.route("/users")
@feature_required("advanced_admin")
@login_required
@admin_required
def users_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users_list.html", users=users)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@feature_required("advanced_admin")
@login_required
@admin_required
def user_new():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if User.query.filter_by(email=email).first():
            flash("A user with that email already exists.", "danger")
            return render_template("admin/user_form.html", user=None, modules=MODULES, actions=ACTIONS)

        user = User(
            full_name=request.form.get("full_name", "").strip(),
            email=email,
            is_admin=bool(request.form.get("is_admin")),
            is_active_user=bool(request.form.get("is_active_user", "on")),
        )
        password = request.form.get("password") or "Welcome@123"
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # get user.id before committing permissions

        if not user.is_admin:
            _save_permissions(user)

        db.session.commit()
        log_action(current_user, f"created user {user.email}", "user_management", user.id)
        flash(f"User '{user.full_name}' created successfully.", "success")
        return redirect(url_for("admin.users_list"))

    return render_template("admin/user_form.html", user=None, modules=MODULES, actions=ACTIONS)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@feature_required("advanced_admin")
@login_required
@admin_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        user.full_name = request.form.get("full_name", "").strip()
        user.is_admin = bool(request.form.get("is_admin"))
        user.is_active_user = bool(request.form.get("is_active_user"))

        new_password = request.form.get("password")
        if new_password:
            user.set_password(new_password)

        # Reset & rewrite permissions
        Permission.query.filter_by(user_id=user.id).delete()
        if not user.is_admin:
            _save_permissions(user)

        db.session.commit()
        log_action(current_user, f"updated user {user.email}", "user_management", user.id)
        flash("User updated successfully.", "success")
        return redirect(url_for("admin.users_list"))

    return render_template("admin/user_form.html", user=user, modules=MODULES, actions=ACTIONS)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@feature_required("advanced_admin")
@login_required
@admin_required
def user_delete(user_id):
    if user_id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin.users_list"))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    log_action(current_user, f"deleted user {user.email}", "user_management", user_id)
    flash("User deleted.", "info")
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/audit-log")
@feature_required("advanced_admin")
@login_required
@admin_required
def audit_log():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(300).all()
    return render_template("admin/audit_log.html", logs=logs)


@admin_bp.route("/users/quick-add", methods=["GET", "POST"])
@login_required
@admin_required
def quick_add_user():
    """Bare-bones 'add a user' form that stays available regardless of the
    advanced_admin feature flag. New users get no module permissions and
    are never admins - flip advanced_admin on in code to assign access."""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()

        if not full_name or not email:
            flash("Name and email are required.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("A user with that email already exists.", "danger")
        else:
            user = User(full_name=full_name, email=email, is_admin=False, is_active_user=True)
            user.set_password(request.form.get("password") or "Welcome@123")
            db.session.add(user)
            db.session.commit()
            log_action(current_user, f"created user {user.email} (quick add)", "user_management", user.id)
            flash(f"User '{user.full_name}' created. No module access is granted yet.", "success")
            return redirect(url_for("admin.quick_add_user"))

    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    return render_template("admin/quick_add_user.html", recent_users=recent_users)


def _save_permissions(user):
    """Read module/action checkboxes (and the 'view all owners' toggle)
    from the submitted form and persist them."""
    for module_key, _label in MODULES:
        flags = {
            f"can_{action}": bool(request.form.get(f"perm__{module_key}__{action}"))
            for action in ACTIONS
        }
        flags["can_view_all"] = bool(request.form.get(f"perm__{module_key}__view_all"))
        if any(flags.values()):
            db.session.add(Permission(user_id=user.id, module=module_key, **flags))


# ---------------------------------------------------------------------------
# DATA VISIBILITY: which other users' owned records can this user see?
# ---------------------------------------------------------------------------
@admin_bp.route("/users/<int:user_id>/data-access", methods=["GET", "POST"])
@feature_required("advanced_admin")
@login_required
@admin_required
def data_access(user_id):
    user = User.query.get_or_404(user_id)
    owner_modules = [m for m in MODULES if m[0] in OWNER_SCOPED_MODULES]
    other_users = User.query.filter(User.id != user.id).order_by(User.full_name).all()

    if request.method == "POST":
        OwnerAccessGrant.query.filter_by(viewer_id=user.id).delete()
        for module_key, _label in owner_modules:
            owner_ids = request.form.getlist(f"grant__{module_key}[]")
            for oid in owner_ids:
                try:
                    oid = int(oid)
                except (TypeError, ValueError):
                    continue
                if oid == user.id:
                    continue
                db.session.add(OwnerAccessGrant(viewer_id=user.id, owner_id=oid, module=module_key))
        db.session.commit()
        log_action(current_user, f"updated data-access grants for {user.email}", "user_management", user.id)
        flash("Data-visibility rules updated.", "success")
        return redirect(url_for("admin.data_access", user_id=user.id))

    existing_grants = {}
    for g in OwnerAccessGrant.query.filter_by(viewer_id=user.id).all():
        existing_grants.setdefault(g.module, set()).add(g.owner_id)

    return render_template(
        "admin/data_access.html",
        user=user,
        owner_modules=owner_modules,
        other_users=other_users,
        existing_grants=existing_grants,
    )


# ---------------------------------------------------------------------------
# LOOKUPS: admin-manageable dropdown values (unit, product category, etc.)
# ---------------------------------------------------------------------------
@admin_bp.route("/lookups")
@login_required
@admin_required
def lookups_list():
    category = request.args.get("category", "")
    categories = [c[0] for c in db.session.query(Lookup.category).distinct().order_by(Lookup.category).all()]
    query = Lookup.query
    if category:
        query = query.filter_by(category=category)
    entries = query.order_by(Lookup.category, Lookup.sort_order, Lookup.value).all()
    return render_template("admin/lookups_list.html", entries=entries, categories=categories, category=category)


@admin_bp.route("/lookups/new", methods=["GET", "POST"])
@login_required
@admin_required
def lookup_new():
    if request.method == "POST":
        category = request.form.get("category", "").strip().lower().replace(" ", "_")
        value = request.form.get("value", "").strip()
        if not category or not value:
            flash("Category and value are required.", "danger")
        elif Lookup.query.filter_by(category=category, value=value).first():
            flash("That value already exists in this category.", "danger")
        else:
            entry = Lookup(
                category=category,
                value=value,
                label=request.form.get("label", "").strip() or None,
                sort_order=int(request.form.get("sort_order") or 0),
                is_active=bool(request.form.get("is_active", "on")),
            )
            db.session.add(entry)
            db.session.commit()
            log_action(current_user, f"created lookup {category}:{value}", "user_management", entry.id)
            flash("Lookup value created.", "success")
            return redirect(url_for("admin.lookups_list", category=category))
    existing_categories = [c[0] for c in db.session.query(Lookup.category).distinct().order_by(Lookup.category).all()]
    return render_template("admin/lookup_form.html", entry=None, existing_categories=existing_categories)


@admin_bp.route("/lookups/<int:lookup_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def lookup_edit(lookup_id):
    entry = Lookup.query.get_or_404(lookup_id)
    if request.method == "POST":
        entry.category = request.form.get("category", entry.category).strip().lower().replace(" ", "_")
        entry.value = request.form.get("value", entry.value).strip()
        entry.label = request.form.get("label", "").strip() or None
        entry.sort_order = int(request.form.get("sort_order") or 0)
        entry.is_active = bool(request.form.get("is_active"))
        db.session.commit()
        log_action(current_user, f"updated lookup {entry.category}:{entry.value}", "user_management", entry.id)
        flash("Lookup value updated.", "success")
        return redirect(url_for("admin.lookups_list", category=entry.category))
    existing_categories = [c[0] for c in db.session.query(Lookup.category).distinct().order_by(Lookup.category).all()]
    return render_template("admin/lookup_form.html", entry=entry, existing_categories=existing_categories)


@admin_bp.route("/lookups/<int:lookup_id>/delete", methods=["POST"])
@login_required
@admin_required
def lookup_delete(lookup_id):
    entry = Lookup.query.get_or_404(lookup_id)
    category = entry.category
    db.session.delete(entry)
    db.session.commit()
    log_action(current_user, f"deleted lookup {category}:{entry.value}", "user_management", lookup_id)
    flash("Lookup value deleted.", "info")
    return redirect(url_for("admin.lookups_list", category=category))
