from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.utils import log_action

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password) and user.is_active_user:
            login_user(user)
            log_action(user, "login", "auth")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))

        flash("Invalid email/password, or your account is deactivated.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    log_action(current_user, "logout", "auth")
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
