import os
from flask import Flask, render_template
from config import config_map
from app.extensions import db, login_manager, csrf


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "default")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_map.get(config_name, config_map["default"]))

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ---- Register blueprints ----
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.vendor import vendor_bp
    from app.blueprints.product import product_bp
    from app.blueprints.purchase import purchase_bp
    from app.blueprints.contacts import contacts_bp
    from app.blueprints.crm import crm_bp
    from app.blueprints.quotation import quotation_bp
    from app.blueprints.sales import sales_bp
    from app.blueprints.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(vendor_bp, url_prefix="/vendors")
    app.register_blueprint(product_bp, url_prefix="/products")
    app.register_blueprint(purchase_bp, url_prefix="/purchase-requests")
    app.register_blueprint(contacts_bp, url_prefix="/contacts")
    app.register_blueprint(crm_bp, url_prefix="/crm")
    app.register_blueprint(quotation_bp, url_prefix="/quotations")
    app.register_blueprint(sales_bp, url_prefix="/sales-orders")
    app.register_blueprint(reports_bp, url_prefix="/reports")

    # ---- Template globals ----
    from app.permissions import has_permission, MODULES, OWNER_SCOPED_MODULES
    from app.feature_flags import feature_enabled

    @app.context_processor
    def inject_globals():
        return dict(
            has_permission=has_permission, ALL_MODULES=MODULES,
            feature_enabled=feature_enabled, owner_scoped_modules=OWNER_SCOPED_MODULES,
        )

    # ---- Error handlers ----
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(401)
    def unauthorized(e):
        return render_template("errors/401.html"), 401

    return app
