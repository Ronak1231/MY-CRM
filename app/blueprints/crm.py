from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Account, Lead, Opportunity, User, LEAD_STATUS, LEAD_SOURCE, OPP_STAGES
from app.permissions import permission_required, apply_owner_scope, can_view_record
from app.utils import log_action, to_float, to_int, get_active_users, get_lookup_values

crm_bp = Blueprint("crm", __name__)


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _owner_id_from_form(default_id=None):
    """Read the 'Owner' select from a submitted form; falls back to `default_id`."""
    raw = request.form.get("owner_id")
    return to_int(raw) if raw else default_id


# ---------------------------------------------------------------------------
# ACCOUNTS
# ---------------------------------------------------------------------------
ACCOUNT_MODULE = "account"


@crm_bp.route("/accounts")
@login_required
@permission_required(ACCOUNT_MODULE, "view")
def list_accounts():
    q = request.args.get("q", "").strip()
    query = apply_owner_scope(Account.query, Account, current_user, ACCOUNT_MODULE)
    if q:
        query = query.filter(Account.name.ilike(f"%{q}%"))
    accounts = query.order_by(Account.name).all()
    return render_template("crm/account_list.html", accounts=accounts, q=q)


@crm_bp.route("/accounts/<int:account_id>")
@login_required
@permission_required(ACCOUNT_MODULE, "view")
def view_account(account_id):
    account = Account.query.get_or_404(account_id)
    if not can_view_record(current_user, ACCOUNT_MODULE, account.owner_id):
        abort(403)
    return render_template("crm/account_view.html", account=account)


@crm_bp.route("/accounts/new", methods=["GET", "POST"])
@login_required
@permission_required(ACCOUNT_MODULE, "create")
def new_account():
    if request.method == "POST":
        account = Account(
            name=request.form["name"].strip(),
            industry=request.form.get("industry"),
            email=request.form.get("email"),
            phone=request.form.get("phone"),
            address=request.form.get("address"),
            city=request.form.get("city"),
            country=request.form.get("country"),
            website=request.form.get("website"),
            is_active=bool(request.form.get("is_active", "on")),
            owner_id=_owner_id_from_form(current_user.id),
        )
        db.session.add(account)
        db.session.commit()
        log_action(current_user, "created account", ACCOUNT_MODULE, account.id)
        flash("Account created successfully.", "success")
        return redirect(url_for("crm.list_accounts"))
    return render_template(
        "crm/account_form.html", account=None,
        users=get_active_users(), industries=get_lookup_values("industry"),
    )


@crm_bp.route("/accounts/<int:account_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required(ACCOUNT_MODULE, "edit")
def edit_account(account_id):
    account = Account.query.get_or_404(account_id)
    if not can_view_record(current_user, ACCOUNT_MODULE, account.owner_id):
        abort(403)
    if request.method == "POST":
        account.name = request.form["name"].strip()
        account.industry = request.form.get("industry")
        account.email = request.form.get("email")
        account.phone = request.form.get("phone")
        account.address = request.form.get("address")
        account.city = request.form.get("city")
        account.country = request.form.get("country")
        account.website = request.form.get("website")
        account.is_active = bool(request.form.get("is_active"))
        account.owner_id = _owner_id_from_form(account.owner_id)
        db.session.commit()
        log_action(current_user, "updated account", ACCOUNT_MODULE, account.id)
        flash("Account updated successfully.", "success")
        return redirect(url_for("crm.view_account", account_id=account.id))
    return render_template(
        "crm/account_form.html", account=account,
        users=get_active_users(), industries=get_lookup_values("industry"),
    )


@crm_bp.route("/accounts/<int:account_id>/delete", methods=["POST"])
@login_required
@permission_required(ACCOUNT_MODULE, "delete")
def delete_account(account_id):
    account = Account.query.get_or_404(account_id)
    if not can_view_record(current_user, ACCOUNT_MODULE, account.owner_id):
        abort(403)
    db.session.delete(account)
    db.session.commit()
    log_action(current_user, "deleted account", ACCOUNT_MODULE, account_id)
    flash("Account deleted.", "info")
    return redirect(url_for("crm.list_accounts"))


# ---------------------------------------------------------------------------
# LEADS
# ---------------------------------------------------------------------------
LEAD_MODULE = "lead"


@crm_bp.route("/leads")
@login_required
@permission_required(LEAD_MODULE, "view")
def list_leads():
    status = request.args.get("status", "")
    query = apply_owner_scope(Lead.query, Lead, current_user, LEAD_MODULE)
    if status:
        query = query.filter_by(status=status)
    leads = query.order_by(Lead.created_at.desc()).all()
    return render_template("crm/lead_list.html", leads=leads, statuses=LEAD_STATUS, status=status)


@crm_bp.route("/leads/new", methods=["GET", "POST"])
@login_required
@permission_required(LEAD_MODULE, "create")
def new_lead():
    if request.method == "POST":
        lead = Lead(
            name=request.form["name"].strip(),
            company_name=request.form.get("company_name"),
            email=request.form.get("email"),
            phone=request.form.get("phone"),
            source=request.form.get("source", "Other"),
            status=request.form.get("status", "New"),
            estimated_value=to_float(request.form.get("estimated_value")),
            notes=request.form.get("notes"),
            owner_id=_owner_id_from_form(current_user.id),
        )
        db.session.add(lead)
        db.session.commit()
        log_action(current_user, "created lead", LEAD_MODULE, lead.id)
        flash("Lead created successfully.", "success")
        return redirect(url_for("crm.list_leads"))
    return render_template(
        "crm/lead_form.html", lead=None, statuses=LEAD_STATUS, sources=LEAD_SOURCE,
        users=get_active_users(),
    )


@crm_bp.route("/leads/<int:lead_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required(LEAD_MODULE, "edit")
def edit_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if not can_view_record(current_user, LEAD_MODULE, lead.owner_id):
        abort(403)
    if request.method == "POST":
        lead.name = request.form["name"].strip()
        lead.company_name = request.form.get("company_name")
        lead.email = request.form.get("email")
        lead.phone = request.form.get("phone")
        lead.source = request.form.get("source", lead.source)
        lead.status = request.form.get("status", lead.status)
        lead.estimated_value = to_float(request.form.get("estimated_value"))
        lead.notes = request.form.get("notes")
        lead.owner_id = _owner_id_from_form(lead.owner_id)
        db.session.commit()
        log_action(current_user, "updated lead", LEAD_MODULE, lead.id)
        flash("Lead updated successfully.", "success")
        return redirect(url_for("crm.list_leads"))
    return render_template(
        "crm/lead_form.html", lead=lead, statuses=LEAD_STATUS, sources=LEAD_SOURCE,
        users=get_active_users(),
    )


@crm_bp.route("/leads/<int:lead_id>/convert", methods=["POST"])
@login_required
@permission_required(LEAD_MODULE, "edit")
@permission_required(ACCOUNT_MODULE, "create")
def convert_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if not can_view_record(current_user, LEAD_MODULE, lead.owner_id):
        abort(403)
    account = Account(
        name=lead.company_name or lead.name,
        email=lead.email,
        phone=lead.phone,
        is_active=True,
        owner_id=lead.owner_id or current_user.id,
    )
    db.session.add(account)
    db.session.flush()

    opportunity = Opportunity(
        name=f"{account.name} - Opportunity",
        account_id=account.id,
        lead_id=lead.id,
        stage="Prospecting",
        amount=lead.estimated_value or 0,
        owner_id=lead.owner_id or current_user.id,
    )
    db.session.add(opportunity)

    lead.status = "Converted"
    lead.account_id = account.id
    db.session.commit()
    log_action(current_user, "converted lead", LEAD_MODULE, lead.id)
    flash("Lead converted into an Account + Opportunity.", "success")
    return redirect(url_for("crm.view_opportunity", opportunity_id=opportunity.id))


@crm_bp.route("/leads/<int:lead_id>/delete", methods=["POST"])
@login_required
@permission_required(LEAD_MODULE, "delete")
def delete_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if not can_view_record(current_user, LEAD_MODULE, lead.owner_id):
        abort(403)
    db.session.delete(lead)
    db.session.commit()
    log_action(current_user, "deleted lead", LEAD_MODULE, lead_id)
    flash("Lead deleted.", "info")
    return redirect(url_for("crm.list_leads"))


# ---------------------------------------------------------------------------
# OPPORTUNITIES
# ---------------------------------------------------------------------------
OPP_MODULE = "opportunity"


@crm_bp.route("/opportunities")
@login_required
@permission_required(OPP_MODULE, "view")
def list_opportunities():
    stage = request.args.get("stage", "")
    query = apply_owner_scope(Opportunity.query, Opportunity, current_user, OPP_MODULE)
    if stage:
        query = query.filter_by(stage=stage)
    opportunities = query.order_by(Opportunity.created_at.desc()).all()
    return render_template("crm/opportunity_list.html", opportunities=opportunities, stages=OPP_STAGES, stage=stage)


@crm_bp.route("/opportunities/<int:opportunity_id>")
@login_required
@permission_required(OPP_MODULE, "view")
def view_opportunity(opportunity_id):
    opportunity = Opportunity.query.get_or_404(opportunity_id)
    if not can_view_record(current_user, OPP_MODULE, opportunity.owner_id):
        abort(403)
    return render_template("crm/opportunity_view.html", opportunity=opportunity, stages=OPP_STAGES)


@crm_bp.route("/opportunities/new", methods=["GET", "POST"])
@login_required
@permission_required(OPP_MODULE, "create")
def new_opportunity():
    if request.method == "POST":
        opportunity = Opportunity(
            name=request.form["name"].strip(),
            account_id=to_int(request.form["account_id"]),
            stage=request.form.get("stage", "Prospecting"),
            amount=to_float(request.form.get("amount")),
            probability=to_int(request.form.get("probability"), 10),
            expected_close_date=_parse_date(request.form.get("expected_close_date")),
            owner_id=_owner_id_from_form(current_user.id),
        )
        db.session.add(opportunity)
        db.session.commit()
        log_action(current_user, "created opportunity", OPP_MODULE, opportunity.id)
        flash("Opportunity created successfully.", "success")
        return redirect(url_for("crm.view_opportunity", opportunity_id=opportunity.id))

    accounts = Account.query.order_by(Account.name).all()
    return render_template(
        "crm/opportunity_form.html", opportunity=None, accounts=accounts, stages=OPP_STAGES,
        users=get_active_users(),
    )


@crm_bp.route("/opportunities/<int:opportunity_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required(OPP_MODULE, "edit")
def edit_opportunity(opportunity_id):
    opportunity = Opportunity.query.get_or_404(opportunity_id)
    if not can_view_record(current_user, OPP_MODULE, opportunity.owner_id):
        abort(403)
    if request.method == "POST":
        opportunity.name = request.form["name"].strip()
        opportunity.account_id = to_int(request.form["account_id"])
        opportunity.stage = request.form.get("stage", opportunity.stage)
        opportunity.amount = to_float(request.form.get("amount"))
        opportunity.probability = to_int(request.form.get("probability"), opportunity.probability)
        opportunity.expected_close_date = _parse_date(request.form.get("expected_close_date"))
        opportunity.close_reason = request.form.get("close_reason")
        opportunity.owner_id = _owner_id_from_form(opportunity.owner_id)
        db.session.commit()
        log_action(current_user, "updated opportunity", OPP_MODULE, opportunity.id)
        flash("Opportunity updated successfully.", "success")
        return redirect(url_for("crm.view_opportunity", opportunity_id=opportunity.id))

    accounts = Account.query.order_by(Account.name).all()
    return render_template(
        "crm/opportunity_form.html", opportunity=opportunity, accounts=accounts, stages=OPP_STAGES,
        users=get_active_users(),
    )


@crm_bp.route("/opportunities/<int:opportunity_id>/close", methods=["POST"])
@login_required
@permission_required(OPP_MODULE, "edit")
def close_opportunity(opportunity_id):
    """Quick action to mark an opportunity Won or Lost from the list/detail view."""
    opportunity = Opportunity.query.get_or_404(opportunity_id)
    if not can_view_record(current_user, OPP_MODULE, opportunity.owner_id):
        abort(403)
    outcome = request.form.get("outcome")  # 'Won' or 'Lost'
    if outcome in ("Won", "Lost"):
        opportunity.stage = outcome
        opportunity.close_reason = request.form.get("close_reason", opportunity.close_reason)
        if outcome == "Won":
            opportunity.probability = 100
        else:
            opportunity.probability = 0
        db.session.commit()
        log_action(current_user, f"marked opportunity as {outcome}", OPP_MODULE, opportunity.id)
        flash(f"Opportunity marked as {outcome}.", "success")
    return redirect(url_for("crm.view_opportunity", opportunity_id=opportunity.id))


@crm_bp.route("/opportunities/<int:opportunity_id>/delete", methods=["POST"])
@login_required
@permission_required(OPP_MODULE, "delete")
def delete_opportunity(opportunity_id):
    opportunity = Opportunity.query.get_or_404(opportunity_id)
    if not can_view_record(current_user, OPP_MODULE, opportunity.owner_id):
        abort(403)
    db.session.delete(opportunity)
    db.session.commit()
    log_action(current_user, "deleted opportunity", OPP_MODULE, opportunity_id)
    flash("Opportunity deleted.", "info")
    return redirect(url_for("crm.list_opportunities"))
