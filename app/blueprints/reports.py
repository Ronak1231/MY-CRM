from datetime import datetime
from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models import SalesOrder, PurchaseRequest
from app.permissions import permission_required
from app.feature_flags import feature_required

reports_bp = Blueprint("reports", __name__)
MODULE = "reports"


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _date_filtered(query, date_field, start, end):
    if start:
        query = query.filter(date_field >= start)
    if end:
        query = query.filter(date_field <= end)
    return query


@reports_bp.route("/sales")
@feature_required("report")
@login_required
@permission_required(MODULE, "view")
def all_sales():
    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))
    query = _date_filtered(SalesOrder.query, SalesOrder.order_date, start, end)
    orders = query.order_by(SalesOrder.order_date.desc()).all()

    total_revenue = sum(float(o.total_amount) for o in orders)
    total_cost = sum(float(o.total_cost) for o in orders)
    total_profit = total_revenue - total_cost

    return render_template(
        "reports/sales.html", orders=orders, start=request.args.get("start", ""),
        end=request.args.get("end", ""), total_revenue=total_revenue,
        total_cost=total_cost, total_profit=total_profit,
    )


@reports_bp.route("/purchase")
@feature_required("report")
@login_required
@permission_required(MODULE, "view")
def all_purchase():
    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))
    query = _date_filtered(PurchaseRequest.query, PurchaseRequest.request_date, start, end)
    prs = query.order_by(PurchaseRequest.request_date.desc()).all()

    total_spend = sum(float(pr.total_amount) for pr in prs)

    return render_template(
        "reports/purchase.html", prs=prs, start=request.args.get("start", ""),
        end=request.args.get("end", ""), total_spend=total_spend,
    )


@reports_bp.route("/profit-loss")
@feature_required("report")
@login_required
@permission_required(MODULE, "view")
def profit_loss():
    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))

    sales_query = _date_filtered(SalesOrder.query, SalesOrder.order_date, start, end)
    orders = sales_query.all()

    purchase_query = _date_filtered(PurchaseRequest.query, PurchaseRequest.request_date, start, end)
    prs = purchase_query.all()

    total_revenue = sum(float(o.total_amount) for o in orders)
    total_cogs = sum(float(o.total_cost) for o in orders)
    gross_profit = total_revenue - total_cogs
    total_purchase_spend = sum(float(pr.total_amount) for pr in prs)
    net_profit = gross_profit - total_purchase_spend

    monthly = {}
    for o in orders:
        key = o.order_date.strftime("%Y-%m") if o.order_date else "Unknown"
        monthly.setdefault(key, {"revenue": 0, "cost": 0})
        monthly[key]["revenue"] += float(o.total_amount)
        monthly[key]["cost"] += float(o.total_cost)
    monthly_sorted = dict(sorted(monthly.items()))

    return render_template(
        "reports/profit_loss.html",
        start=request.args.get("start", ""), end=request.args.get("end", ""),
        total_revenue=total_revenue, total_cogs=total_cogs, gross_profit=gross_profit,
        total_purchase_spend=total_purchase_spend, net_profit=net_profit,
        monthly=monthly_sorted,
    )
