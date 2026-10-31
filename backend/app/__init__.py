from flask import Flask
from app.config import Config
from app.extensions import db, migrate, jwt, cors


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # Import models so Alembic sees them
    with app.app_context():
        from app.models import user, product, plan, tax, discount  # noqa
        from app.models import quotation, subscription, invoice, payment  # noqa

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.products import products_bp
    from app.routes.plans import plans_bp
    from app.routes.quotations import quotations_bp
    from app.routes.subscriptions import subscriptions_bp
    from app.routes.billing import billing_bp
    from app.routes.invoices import invoices_bp
    from app.routes.taxes import taxes_bp
    from app.routes.discounts import discounts_bp
    from app.routes.payments import payments_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.radar import radar_bp

    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(users_bp, url_prefix='/api/v1/users')
    app.register_blueprint(products_bp, url_prefix='/api/v1/products')
    app.register_blueprint(plans_bp, url_prefix='/api/v1/plans')
    app.register_blueprint(quotations_bp, url_prefix='/api/v1/quotations')
    app.register_blueprint(subscriptions_bp, url_prefix='/api/v1/subscriptions')
    app.register_blueprint(billing_bp, url_prefix='/api/v1/billing')
    app.register_blueprint(invoices_bp, url_prefix='/api/v1/invoices')
    app.register_blueprint(taxes_bp, url_prefix='/api/v1/taxes')
    app.register_blueprint(discounts_bp, url_prefix='/api/v1/discounts')
    app.register_blueprint(payments_bp, url_prefix='/api/v1/payments')
    app.register_blueprint(dashboard_bp, url_prefix='/api/v1/dashboard')
    app.register_blueprint(radar_bp, url_prefix='/api/v1/radar')

    @app.route('/api/v1/health')
    def health():
        return {'status': 'ok', 'service': 'Brightloop SMS API'}

    return app
