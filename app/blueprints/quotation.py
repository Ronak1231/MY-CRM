from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (
    Quotation, QuotationItem, Account, Product, ContactPerson, Opportunity,
    SalesOrder, SalesOrderItem, QUOTE_STATUS,
)
from app.permissions import permission_required, apply_owner_scope, can_view_record
from app.feature_flags import feature_required
from app.utils import log_action, to_float, to_int, generate_number, get_active_users

quotation_bp = Blueprint("quotation", __name__)
MODULE = "quotation"


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
        items.append(QuotationItem(
            product_id=to_int(pid), quantity=to_int(qty, 1),
            unit_price=to_float(price), discount_pct=to_float(disc),
        ))
    return items


@quotation_bp.route("/")
@feature_required("quotation")
@login_required
@permission_required(MODULE, "view")
def list_quotations():
    status = request.args.get("status", "")
    query = apply_owner_scope(Quotation.query, Quotation, current_user, MODULE)
    if status:
        query = query.filter_by(status=status)
    quotes = query.order_by(Quotation.created_at.desc()).all()
    return render_template("quotation/list.html", quotes=quotes, statuses=QUOTE_STATUS, status=status)


@quotation_bp.route("/<int:quote_id>")
@feature_required("quotation")
@login_required
@permission_required(MODULE, "view")
def view_quotation(quote_id):
    quote = Quotation.query.get_or_404(quote_id)
    if not can_view_record(current_user, MODULE, quote.owner_id):
        abort(403)
    return render_template("quotation/view.html", quote=quote, statuses=QUOTE_STATUS)


@quotation_bp.route("/new", methods=["GET", "POST"])
@feature_required("quotation")
@login_required
@permission_required(MODULE, "create")
def new_quotation():
    if request.method == "POST":
        quote = Quotation(
            quote_number=generate_number(Quotation, "quote_number", "QT"),
            account_id=to_int(request.form["account_id"]),
            contact_person_id=to_int(request.form.get("contact_person_id")) or None,
            opportunity_id=to_int(request.form.get("opportunity_id")) or None,
            status=request.form.get("status", "Draft"),
            valid_until=_parse_date(request.form.get("valid_until")),
            notes=request.form.get("notes"),
            created_by_id=current_user.id,
            owner_id=_owner_id_from_form(current_user.id),
        )
        quote.items = _parse_items(request.form)
        db.session.add(quote)
        db.session.commit()
        log_action(current_user, "created quotation", MODULE, quote.id)
        flash(f"Quotation {quote.quote_number} created.", "success")
        return redirect(url_for("quotation.view_quotation", quote_id=quote.id))

    return render_template("quotation/form.html", quote=None, **_form_context())


@quotation_bp.route("/<int:quote_id>/edit", methods=["GET", "POST"])
@feature_required("quotation")
@login_required
@permission_required(MODULE, "edit")
def edit_quotation(quote_id):
    quote = Quotation.query.get_or_404(quote_id)
    if not can_view_record(current_user, MODULE, quote.owner_id):
        abort(403)
    if request.method == "POST":
        quote.account_id = to_int(request.form["account_id"])
        quote.contact_person_id = to_int(request.form.get("contact_person_id")) or None
        quote.opportunity_id = to_int(request.form.get("opportunity_id")) or None
        quote.status = request.form.get("status", quote.status)
        quote.valid_until = _parse_date(request.form.get("valid_until"))
        quote.notes = request.form.get("notes")
        quote.items = _parse_items(request.form)
        quote.owner_id = _owner_id_from_form(quote.owner_id)
        db.session.commit()
        log_action(current_user, "updated quotation", MODULE, quote.id)
        flash("Quotation updated.", "success")
        return redirect(url_for("quotation.view_quotation", quote_id=quote.id))

    return render_template("quotation/form.html", quote=quote, **_form_context())


@quotation_bp.route("/<int:quote_id>/convert", methods=["POST"])
@feature_required("quotation")
@feature_required("sales_order")
@login_required
@permission_required(MODULE, "edit")
@permission_required("sales_order", "create")
def convert_to_sales_order(quote_id):
    quote = Quotation.query.get_or_404(quote_id)
    if not can_view_record(current_user, MODULE, quote.owner_id):
        abort(403)
    if quote.sales_order:
        flash("This quotation has already been converted to a Sales Order.", "warning")
        return redirect(url_for("quotation.view_quotation", quote_id=quote.id))

    order = SalesOrder(
        so_number=generate_number(SalesOrder, "so_number", "SO"),
        account_id=quote.account_id,
        contact_person_id=quote.contact_person_id,
        quotation_id=quote.id,
        status="Pending",
        created_by_id=current_user.id,
        owner_id=quote.owner_id or current_user.id,
    )
    order.items = [
        SalesOrderItem(
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount_pct=item.discount_pct,
        )
        for item in quote.items
    ]
    quote.status = "Converted"
    db.session.add(order)
    db.session.commit()
    log_action(current_user, "converted quotation to sales order", MODULE, quote.id)
    flash(f"Sales Order {order.so_number} created from quotation.", "success")
    return redirect(url_for("sales.view_sales_order", so_id=order.id))


@quotation_bp.route("/<int:quote_id>/delete", methods=["POST"])
@feature_required("quotation")
@login_required
@permission_required(MODULE, "delete")
def delete_quotation(quote_id):
    quote = Quotation.query.get_or_404(quote_id)
    if not can_view_record(current_user, MODULE, quote.owner_id):
        abort(403)
    db.session.delete(quote)
    db.session.commit()
    log_action(current_user, "deleted quotation", MODULE, quote_id)
    flash("Quotation deleted.", "info")
    return redirect(url_for("quotation.list_quotations"))


def _form_context():
    return dict(
        accounts=Account.query.order_by(Account.name).all(),
        products=Product.query.filter_by(is_active=True).order_by(Product.name).all(),
        contacts=ContactPerson.query.filter_by(contact_type="sales").all(),
        opportunities=Opportunity.query.filter(Opportunity.stage.notin_(["Won", "Lost"])).all(),
        statuses=QUOTE_STATUS,
        users=get_active_users(),
    )
