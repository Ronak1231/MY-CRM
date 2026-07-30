from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import ContactPerson, Vendor, Account
from app.permissions import permission_required, apply_owner_scope, can_view_record
from app.utils import log_action, get_active_users, to_int

contacts_bp = Blueprint("contacts", __name__)


def _owner_id_from_form(default_id=None):
    raw = request.form.get("owner_id")
    return to_int(raw) if raw else default_id


# ---------------------------------------------------------------------------
# PURCHASE-SIDE CONTACTS (linked to Vendors)
# ---------------------------------------------------------------------------
PURCHASE_MODULE = "contact_purchase"


@contacts_bp.route("/purchase")
@login_required
@permission_required(PURCHASE_MODULE, "view")
def list_purchase_contacts():
    query = apply_owner_scope(
        ContactPerson.query.filter_by(contact_type="purchase"), ContactPerson, current_user, PURCHASE_MODULE
    )
    contacts = query.order_by(ContactPerson.name).all()
    return render_template("contacts/list.html", contacts=contacts, kind="purchase")


@contacts_bp.route("/purchase/new", methods=["GET", "POST"])
@login_required
@permission_required(PURCHASE_MODULE, "create")
def new_purchase_contact():
    if request.method == "POST":
        contact = ContactPerson(
            contact_type="purchase",
            name=request.form["name"].strip(),
            designation=request.form.get("designation"),
            email=request.form.get("email"),
            phone=request.form.get("phone"),
            is_primary=bool(request.form.get("is_primary")),
            notes=request.form.get("notes"),
            vendor_id=request.form.get("vendor_id") or None,
            owner_id=_owner_id_from_form(current_user.id),
        )
        db.session.add(contact)
        db.session.commit()
        log_action(current_user, "created purchase contact", PURCHASE_MODULE, contact.id)
        flash("Purchase contact created.", "success")
        return redirect(url_for("contacts.list_purchase_contacts"))

    vendors = Vendor.query.order_by(Vendor.name).all()
    return render_template(
        "contacts/form.html", contact=None, kind="purchase", vendors=vendors, accounts=None,
        users=get_active_users(),
    )


@contacts_bp.route("/purchase/<int:contact_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required(PURCHASE_MODULE, "edit")
def edit_purchase_contact(contact_id):
    contact = ContactPerson.query.get_or_404(contact_id)
    if not can_view_record(current_user, PURCHASE_MODULE, contact.owner_id):
        abort(403)
    if request.method == "POST":
        contact.name = request.form["name"].strip()
        contact.designation = request.form.get("designation")
        contact.email = request.form.get("email")
        contact.phone = request.form.get("phone")
        contact.is_primary = bool(request.form.get("is_primary"))
        contact.notes = request.form.get("notes")
        contact.vendor_id = request.form.get("vendor_id") or None
        contact.owner_id = _owner_id_from_form(contact.owner_id)
        db.session.commit()
        log_action(current_user, "updated purchase contact", PURCHASE_MODULE, contact.id)
        flash("Purchase contact updated.", "success")
        return redirect(url_for("contacts.list_purchase_contacts"))

    vendors = Vendor.query.order_by(Vendor.name).all()
    return render_template(
        "contacts/form.html", contact=contact, kind="purchase", vendors=vendors, accounts=None,
        users=get_active_users(),
    )


@contacts_bp.route("/purchase/<int:contact_id>/delete", methods=["POST"])
@login_required
@permission_required(PURCHASE_MODULE, "delete")
def delete_purchase_contact(contact_id):
    contact = ContactPerson.query.get_or_404(contact_id)
    if not can_view_record(current_user, PURCHASE_MODULE, contact.owner_id):
        abort(403)
    db.session.delete(contact)
    db.session.commit()
    log_action(current_user, "deleted purchase contact", PURCHASE_MODULE, contact_id)
    flash("Purchase contact deleted.", "info")
    return redirect(url_for("contacts.list_purchase_contacts"))


# ---------------------------------------------------------------------------
# SALES-SIDE CONTACTS (linked to Accounts)
# ---------------------------------------------------------------------------
SALES_MODULE = "contact_sales"


@contacts_bp.route("/sales")
@login_required
@permission_required(SALES_MODULE, "view")
def list_sales_contacts():
    query = apply_owner_scope(
        ContactPerson.query.filter_by(contact_type="sales"), ContactPerson, current_user, SALES_MODULE
    )
    contacts = query.order_by(ContactPerson.name).all()
    return render_template("contacts/list.html", contacts=contacts, kind="sales")


@contacts_bp.route("/sales/new", methods=["GET", "POST"])
@login_required
@permission_required(SALES_MODULE, "create")
def new_sales_contact():
    if request.method == "POST":
        contact = ContactPerson(
            contact_type="sales",
            name=request.form["name"].strip(),
            designation=request.form.get("designation"),
            email=request.form.get("email"),
            phone=request.form.get("phone"),
            is_primary=bool(request.form.get("is_primary")),
            notes=request.form.get("notes"),
            account_id=request.form.get("account_id") or None,
            owner_id=_owner_id_from_form(current_user.id),
        )
        db.session.add(contact)
        db.session.commit()
        log_action(current_user, "created sales contact", SALES_MODULE, contact.id)
        flash("Sales contact created.", "success")
        return redirect(url_for("contacts.list_sales_contacts"))

    accounts = Account.query.order_by(Account.name).all()
    return render_template(
        "contacts/form.html", contact=None, kind="sales", vendors=None, accounts=accounts,
        users=get_active_users(),
    )


@contacts_bp.route("/sales/<int:contact_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required(SALES_MODULE, "edit")
def edit_sales_contact(contact_id):
    contact = ContactPerson.query.get_or_404(contact_id)
    if not can_view_record(current_user, SALES_MODULE, contact.owner_id):
        abort(403)
    if request.method == "POST":
        contact.name = request.form["name"].strip()
        contact.designation = request.form.get("designation")
        contact.email = request.form.get("email")
        contact.phone = request.form.get("phone")
        contact.is_primary = bool(request.form.get("is_primary"))
        contact.notes = request.form.get("notes")
        contact.account_id = request.form.get("account_id") or None
        contact.owner_id = _owner_id_from_form(contact.owner_id)
        db.session.commit()
        log_action(current_user, "updated sales contact", SALES_MODULE, contact.id)
        flash("Sales contact updated.", "success")
        return redirect(url_for("contacts.list_sales_contacts"))

    accounts = Account.query.order_by(Account.name).all()
    return render_template(
        "contacts/form.html", contact=contact, kind="sales", vendors=None, accounts=accounts,
        users=get_active_users(),
    )


@contacts_bp.route("/sales/<int:contact_id>/delete", methods=["POST"])
@login_required
@permission_required(SALES_MODULE, "delete")
def delete_sales_contact(contact_id):
    contact = ContactPerson.query.get_or_404(contact_id)
    if not can_view_record(current_user, SALES_MODULE, contact.owner_id):
        abort(403)
    db.session.delete(contact)
    db.session.commit()
    log_action(current_user, "deleted sales contact", SALES_MODULE, contact_id)
    flash("Sales contact deleted.", "info")
    return redirect(url_for("contacts.list_sales_contacts"))
