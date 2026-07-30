from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import SalesOrder, SalesOrderItem, Account, Product, ContactPerson, SO_STATUS
from app.permissions import permission_required, apply_owner_scope, can_view_record
from app.feature_flags import feature_required
from app.utils import log_action, to_float, to_int, generate_number, get_active_users

sales_bp = Blueprint("sales", __name__)
MODULE = "sales_order"


def _owner_id_from_form(default_id=None):
    raw = request.form.get("owner_id")
    return to_int(raw) if raw else default_id


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_items(form):
    items = []
    product_ids = form.getlist("product_id[]")
    quantities = form.getlist("quantity[]")
    prices = form.getlist("unit_price[]")
    discounts = form.getlist("discount_pct[]")
    for pid, qty, price, disc in zip(product_ids, quantities, prices, discounts):
        if not pid:
            continue
        items.append(SalesOrderItem(
            product_id=to_int(pid), quantity=to_int(qty, 1),
            unit_price=to_float(price), discount_pct=to_float(disc),
        ))
    return items


@sales_bp.route("/")
@feature_required("sales_order")
@login_required
@permission_required(MODULE, "view")
def list_sales_orders():
    status = request.args.get("status", "")
    query = apply_owner_scope(SalesOrder.query, SalesOrder, current_user, MODULE)
    if status:
        query = query.filter_by(status=status)
    orders = query.order_by(SalesOrder.created_at.desc()).all()
    return render_template("sales/list.html", orders=orders, statuses=SO_STATUS, status=status)


@sales_bp.route("/<int:so_id>")
@feature_required("sales_order")
@login_required
@permission_required(MODULE, "view")
def view_sales_order(so_id):
    order = SalesOrder.query.get_or_404(so_id)
    if not can_view_record(current_user, MODULE, order.owner_id):
        abort(403)
    return render_template("sales/view.html", order=order, statuses=SO_STATUS)


@sales_bp.route("/new", methods=["GET", "POST"])
@feature_required("sales_order")
@login_required
@permission_required(MODULE, "create")
def new_sales_order():
    if request.method == "POST":
        order = SalesOrder(
            so_number=generate_number(SalesOrder, "so_number", "SO"),
            account_id=to_int(request.form["account_id"]),
            contact_person_id=to_int(request.form.get("contact_person_id")) or None,
            status=request.form.get("status", "Pending"),
            delivery_date=_parse_date(request.form.get("delivery_date")),
            notes=request.form.get("notes"),
            created_by_id=current_user.id,
            owner_id=_owner_id_from_form(current_user.id),
        )
        order.items = _parse_items(request.form)
        db.session.add(order)
        db.session.commit()
        log_action(current_user, "created sales order", MODULE, order.id)
        flash(f"Sales Order {order.so_number} created.", "success")
        return redirect(url_for("sales.view_sales_order", so_id=order.id))

    return render_template("sales/form.html", order=None, **_form_context())


@sales_bp.route("/<int:so_id>/edit", methods=["GET", "POST"])
@feature_required("sales_order")
@login_required
@permission_required(MODULE, "edit")
def edit_sales_order(so_id):
    order = SalesOrder.query.get_or_404(so_id)
    if not can_view_record(current_user, MODULE, order.owner_id):
        abort(403)
    if request.method == "POST":
        order.account_id = to_int(request.form["account_id"])
        order.contact_person_id = to_int(request.form.get("contact_person_id")) or None
        order.status = request.form.get("status", order.status)
        order.delivery_date = _parse_date(request.form.get("delivery_date"))
        order.notes = request.form.get("notes")
        order.items = _parse_items(request.form)
        order.owner_id = _owner_id_from_form(order.owner_id)
        db.session.commit()
        log_action(current_user, "updated sales order", MODULE, order.id)
        flash("Sales Order updated.", "success")
        return redirect(url_for("sales.view_sales_order", so_id=order.id))

    return render_template("sales/form.html", order=order, **_form_context())


@sales_bp.route("/<int:so_id>/delete", methods=["POST"])
@feature_required("sales_order")
@login_required
@permission_required(MODULE, "delete")
def delete_sales_order(so_id):
    order = SalesOrder.query.get_or_404(so_id)
    if not can_view_record(current_user, MODULE, order.owner_id):
        abort(403)
    db.session.delete(order)
    db.session.commit()
    log_action(current_user, "deleted sales order", MODULE, so_id)
    flash("Sales Order deleted.", "info")
    return redirect(url_for("sales.list_sales_orders"))


def _form_context():
    return dict(
        accounts=Account.query.order_by(Account.name).all(),
        products=Product.query.filter_by(is_active=True).order_by(Product.name).all(),
        contacts=ContactPerson.query.filter_by(contact_type="sales").all(),
        statuses=SO_STATUS,
        users=get_active_users(),
    )
