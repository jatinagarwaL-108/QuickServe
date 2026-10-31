import os

from flask import Flask
from flask_login import current_user
from werkzeug.security import generate_password_hash

from .config import Config, BASE_DIR
from .extensions import db, login_manager


def create_app(config_class=Config):
    # templates/ and static/ stay in the project root
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, 'templates'),
        static_folder=os.path.join(BASE_DIR, 'static'),
    )
    app.config.from_object(config_class)

    if not app.config.get('SECRET_KEY'):
        raise RuntimeError(
            "SECRET_KEY is not set. Locally, put SECRET_KEY=something-long in a "
            ".env file. On Render, add it under Environment."
        )

    db.init_app(app)
    login_manager.init_app(app)

    # Importing the models registers the tables
    from . import models  # noqa: F401

    # Blueprints: add one line here each time you finish moving a route file
    from .routes import auth, main, customer, provider, admin
    for module in (auth, main, customer, provider, admin):
        app.register_blueprint(module.bp)

    @app.context_processor
    def inject_provider_notifications():
        """Make the provider's pending count available in every template."""
        from .models import Booking
        pending_count = 0
        if current_user.is_authenticated and current_user.role == "provider":
            pending_count = Booking.query.filter_by(
                provider_id=current_user.id, status="Pending").count()
        return dict(provider_pending_count=pending_count)

    with app.app_context():
        db.create_all()  # creates MISSING tables only, never deletes anything
        _create_admin_from_env()

    return app


def _create_admin_from_env():
    """Create the first admin from ADMIN_EMAIL / ADMIN_PASSWORD, if both are set."""
    from .models import User
    email = os.environ.get('ADMIN_EMAIL')
    password = os.environ.get('ADMIN_PASSWORD')
    if not (email and password):
        return
    if User.query.filter_by(role='admin').first():
        return
    db.session.add(User(
        username='admin',
        email=email,
        password=generate_password_hash(password, method='pbkdf2:sha256'),
        role='admin',
    ))
    db.session.commit()