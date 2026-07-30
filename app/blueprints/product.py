from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Product
from app.permissions import permission_required, apply_owner_scope, can_view_record
from app.utils import log_action, to_float, to_int, get_active_users, get_lookup_values

product_bp = Blueprint("product", __name__)
MODULE = "product"


def _owner_id_from_form(default_id=None):
    raw = request.form.get("owner_id")
    return to_int(raw) if raw else default_id


def _form_context():
    return dict(
        users=get_active_users(),
        units=get_lookup_values("unit"),
        categories=get_lookup_values("product_category"),
    )


@product_bp.route("/")
@login_required
@permission_required(MODULE, "view")
def list_products():
    q = request.args.get("q", "").strip()
    query = apply_owner_scope(Product.query, Product, current_user, MODULE)
    if q:
        query = query.filter(
            (Product.name.ilike(f"%{q}%")) | (Product.sku.ilike(f"%{q}%"))
        )
    products = query.order_by(Product.name).all()
    return render_template("product/list.html", products=products, q=q)


@product_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required(MODULE, "create")
def new_product():
    if request.method == "POST":
        product = Product(
            sku=request.form["sku"].strip(),
            name=request.form["name"].strip(),
            description=request.form.get("description"),
            category=request.form.get("category"),
            unit=request.form.get("unit", "pcs"),
            cost_price=to_float(request.form.get("cost_price")),
            selling_price=to_float(request.form.get("selling_price")),
            stock_qty=to_int(request.form.get("stock_qty")),
            reorder_level=to_int(request.form.get("reorder_level")),
            is_active=bool(request.form.get("is_active", "on")),
            owner_id=_owner_id_from_form(current_user.id),
        )
        db.session.add(product)
        db.session.commit()
        log_action(current_user, "created product", MODULE, product.id)
        flash("Product created successfully.", "success")
        return redirect(url_for("product.list_products"))
    return render_template("product/form.html", product=None, **_form_context())


@product_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required(MODULE, "edit")
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if not can_view_record(current_user, MODULE, product.owner_id):
        abort(403)
    if request.method == "POST":
        product.sku = request.form["sku"].strip()
        product.name = request.form["name"].strip()
        product.description = request.form.get("description")
        product.category = request.form.get("category")
        product.unit = request.form.get("unit", "pcs")
        product.cost_price = to_float(request.form.get("cost_price"))
        product.selling_price = to_float(request.form.get("selling_price"))
        product.stock_qty = to_int(request.form.get("stock_qty"))
        product.reorder_level = to_int(request.form.get("reorder_level"))
        product.is_active = bool(request.form.get("is_active"))
        product.owner_id = _owner_id_from_form(product.owner_id)
        db.session.commit()
        log_action(current_user, "updated product", MODULE, product.id)
        flash("Product updated successfully.", "success")
        return redirect(url_for("product.list_products"))
    return render_template("product/form.html", product=product, **_form_context())


@product_bp.route("/<int:product_id>/delete", methods=["POST"])
@login_required
@permission_required(MODULE, "delete")
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if not can_view_record(current_user, MODULE, product.owner_id):
        abort(403)
    db.session.delete(product)
    db.session.commit()
    log_action(current_user, "deleted product", MODULE, product_id)
    flash("Product deleted.", "info")
    return redirect(url_for("product.list_products"))
