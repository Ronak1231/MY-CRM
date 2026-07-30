from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Vendor
from app.permissions import permission_required, apply_owner_scope, can_view_record
from app.utils import log_action, get_active_users, get_lookup_values, to_int

vendor_bp = Blueprint("vendor", __name__)
MODULE = "vendor"


def _owner_id_from_form(default_id=None):
    raw = request.form.get("owner_id")
    return to_int(raw) if raw else default_id


@vendor_bp.route("/")
@login_required
@permission_required(MODULE, "view")
def list_vendors():
    q = request.args.get("q", "").strip()
    query = apply_owner_scope(Vendor.query, Vendor, current_user, MODULE)
    if q:
        query = query.filter(Vendor.name.ilike(f"%{q}%"))
    vendors = query.order_by(Vendor.name).all()
    return render_template("vendor/list.html", vendors=vendors, q=q)


@vendor_bp.route("/<int:vendor_id>")
@login_required
@permission_required(MODULE, "view")
def view_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    if not can_view_record(current_user, MODULE, vendor.owner_id):
        abort(403)
    return render_template("vendor/view.html", vendor=vendor)


@vendor_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required(MODULE, "create")
def new_vendor():
    if request.method == "POST":
        vendor = Vendor(
            name=request.form["name"].strip(),
            company_reg_no=request.form.get("company_reg_no"),
            email=request.form.get("email"),
            phone=request.form.get("phone"),
            address=request.form.get("address"),
            city=request.form.get("city"),
            country=request.form.get("country"),
            gst_number=request.form.get("gst_number"),
            payment_terms=request.form.get("payment_terms"),
            is_active=bool(request.form.get("is_active", "on")),
            owner_id=_owner_id_from_form(current_user.id),
        )
        db.session.add(vendor)
        db.session.commit()
        log_action(current_user, "created vendor", MODULE, vendor.id)
        flash("Vendor created successfully.", "success")
        return redirect(url_for("vendor.list_vendors"))
    return render_template(
        "vendor/form.html", vendor=None,
        users=get_active_users(), payment_terms_options=get_lookup_values("payment_terms"),
    )


@vendor_bp.route("/<int:vendor_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required(MODULE, "edit")
def edit_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    if not can_view_record(current_user, MODULE, vendor.owner_id):
        abort(403)
    if request.method == "POST":
        vendor.name = request.form["name"].strip()
        vendor.company_reg_no = request.form.get("company_reg_no")
        vendor.email = request.form.get("email")
        vendor.phone = request.form.get("phone")
        vendor.address = request.form.get("address")
        vendor.city = request.form.get("city")
        vendor.country = request.form.get("country")
        vendor.gst_number = request.form.get("gst_number")
        vendor.payment_terms = request.form.get("payment_terms")
        vendor.is_active = bool(request.form.get("is_active"))
        vendor.owner_id = _owner_id_from_form(vendor.owner_id)
        db.session.commit()
        log_action(current_user, "updated vendor", MODULE, vendor.id)
        flash("Vendor updated successfully.", "success")
        return redirect(url_for("vendor.view_vendor", vendor_id=vendor.id))
    return render_template(
        "vendor/form.html", vendor=vendor,
        users=get_active_users(), payment_terms_options=get_lookup_values("payment_terms"),
    )


@vendor_bp.route("/<int:vendor_id>/delete", methods=["POST"])
@login_required
@permission_required(MODULE, "delete")
def delete_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    if not can_view_record(current_user, MODULE, vendor.owner_id):
        abort(403)
    db.session.delete(vendor)
    db.session.commit()
    log_action(current_user, "deleted vendor", MODULE, vendor_id)
    flash("Vendor deleted.", "info")
    return redirect(url_for("vendor.list_vendors"))
