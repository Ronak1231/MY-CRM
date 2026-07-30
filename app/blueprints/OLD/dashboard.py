from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import (
    Vendor, Product, PurchaseRequest, Account, Lead, Opportunity,
    Quotation, SalesOrder,
)
from app.permissions import has_permission

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    stats = {}

    if has_permission(current_user, "vendor", "view"):
        stats["vendors"] = Vendor.query.count()
    if has_permission(current_user, "product", "view"):
        stats["products"] = Product.query.count()
    if has_permission(current_user, "purchase_request", "view"):
        stats["purchase_requests"] = PurchaseRequest.query.count()
    if has_permission(current_user, "account", "view"):
        stats["accounts"] = Account.query.count()
    if has_permission(current_user, "lead", "view"):
        stats["leads"] = Lead.query.count()
    if has_permission(current_user, "opportunity", "view"):
        opps = Opportunity.query.all()
        stats["opportunities"] = len(opps)
        stats["opportunities_open"] = len([o for o in opps if o.stage not in ("Won", "Lost")])
        stats["opportunities_won"] = len([o for o in opps if o.stage == "Won"])
        stats["opportunities_lost"] = len([o for o in opps if o.stage == "Lost"])
        stats["pipeline_value"] = sum(
            float(o.amount or 0) for o in opps if o.stage not in ("Won", "Lost")
        )
    if has_permission(current_user, "quotation", "view"):
        stats["quotations"] = Quotation.query.count()
    if has_permission(current_user, "sales_order", "view"):
        orders = SalesOrder.query.all()
        stats["sales_orders"] = len(orders)
        stats["sales_revenue"] = sum(float(o.total_amount or 0) for o in orders)
        stats["sales_profit"] = sum(float(o.profit or 0) for o in orders)

    return render_template("dashboard/index.html", stats=stats)
