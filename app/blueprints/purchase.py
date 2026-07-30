from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import PurchaseRequest, PurchaseRequestItem, Vendor, Product, PR_STATUS
from app.permissions import permission_required, apply_owner_scope, can_view_record
from app.feature_flags import feature_required
from app.utils import log_action, to_float, to_int, generate_number, get_active_users
from datetime import datetime

purchase_bp = Blueprint("purchase", __name__)
MODULE = "purchase_request"


def _owner_id_from_form(default_id=None):
    raw = request.form.get("owner_id")
    return to_int(raw) if raw else default_id


def _parse_items(form):
    items = []
    product_ids = form.getlist("product_id[]")
    quantities = form.getlist("quantity[]")
    costs = form.getlist("unit_cost[]")
    for pid, qty, cost in zip(product_ids, quantities, costs):
        if not pid:
            continue
        items.append(PurchaseRequestItem(
            product_id=to_int(pid), quantity=to_int(qty, 1), unit_cost=to_float(cost)
        ))
    return items


@purchase_bp.route("/")
@feature_required("purchase_request")
@login_required
@permission_required(MODULE, "view")
def list_purchase_requests():
    status = request.args.get("status", "")
    query = apply_owner_scope(PurchaseRequest.query, PurchaseRequest, current_user, MODULE)
    if status:
        query = query.filter_by(status=status)
    prs = query.order_by(PurchaseRequest.created_at.desc()).all()
    return render_template("purchase/list.html", prs=prs, statuses=PR_STATUS, status=status)


@purchase_bp.route("/<int:pr_id>")
@feature_required("purchase_request")
@login_required
@permission_required(MODULE, "view")
def view_purchase_request(pr_id):
    pr = PurchaseRequest.query.get_or_404(pr_id)
    if not can_view_record(current_user, MODULE, pr.owner_id):
        abort(403)
    return render_template("purchase/view.html", pr=pr, statuses=PR_STATUS)


@purchase_bp.route("/new", methods=["GET", "POST"])
@feature_required("purchase_request")
@login_required
@permission_required(MODULE, "create")
def new_purchase_request():
    if request.method == "POST":
        pr = PurchaseRequest(
            pr_number=generate_number(PurchaseRequest, "pr_number", "PR"),
            vendor_id=to_int(request.form["vendor_id"]),
            contact_person_id=to_int(request.form.get("contact_person_id")) or None,
            status=request.form.get("status", "Draft"),
            expected_date=_parse_date(request.form.get("expected_date")),
            notes=request.form.get("notes"),
            created_by_id=current_user.id,
            owner_id=_owner_id_from_form(current_user.id),
        )
        pr.items = _parse_items(request.form)
        db.session.add(pr)
        db.session.commit()
        log_action(current_user, "created purchase request", MODULE, pr.id)
        flash(f"Purchase Request {pr.pr_number} created.", "success")
        return redirect(url_for("purchase.view_purchase_request", pr_id=pr.id))

    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    return render_template(
        "purchase/form.html", pr=None, vendors=vendors, products=products, statuses=PR_STATUS,
        users=get_active_users(),
    )


@purchase_bp.route("/<int:pr_id>/edit", methods=["GET", "POST"])
@feature_required("purchase_request")
@login_required
@permission_required(MODULE, "edit")
def edit_purchase_request(pr_id):
    pr = PurchaseRequest.query.get_or_404(pr_id)
    if not can_view_record(current_user, MODULE, pr.owner_id):
        abort(403)
    if request.method == "POST":
        pr.vendor_id = to_int(request.form["vendor_id"])
        pr.contact_person_id = to_int(request.form.get("contact_person_id")) or None
        pr.status = request.form.get("status", pr.status)
        pr.expected_date = _parse_date(request.form.get("expected_date"))
        pr.notes = request.form.get("notes")
        pr.items = _parse_items(request.form)
        pr.owner_id = _owner_id_from_form(pr.owner_id)
        db.session.commit()
        log_action(current_user, "updated purchase request", MODULE, pr.id)
        flash("Purchase Request updated.", "success")
        return redirect(url_for("purchase.view_purchase_request", pr_id=pr.id))

    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    return render_template(
        "purchase/form.html", pr=pr, vendors=vendors, products=products, statuses=PR_STATUS,
        users=get_active_users(),
    )


@purchase_bp.route("/<int:pr_id>/delete", methods=["POST"])
@feature_required("purchase_request")
@login_required
@permission_required(MODULE, "delete")
def delete_purchase_request(pr_id):
    pr = PurchaseRequest.query.get_or_404(pr_id)
    if not can_view_record(current_user, MODULE, pr.owner_id):
        abort(403)
    db.session.delete(pr)
    db.session.commit()
    log_action(current_user, "deleted purchase request", MODULE, pr_id)
    flash("Purchase Request deleted.", "info")
    return redirect(url_for("purchase.list_purchase_requests"))


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
