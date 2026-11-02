import os

from flask import Flask
from flask_login import current_user
from werkzeug.security import generate_password_hash

from .config import Config, BASE_DIR
from .extensions import db, login_manager, migrate  # CHANGED: migrate added


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
    migrate.init_app(app, db)  # NEW

    # Importing the models lets Flask-Migrate see your tables
    from . import models  # noqa: F401

    from .routes import auth, main, customer, provider, admin,assistant
    for module in (auth, main, customer, provider, admin,assistant):
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

    # NEW: replaces db.create_all() and the automatic admin creation.
    # Run it once per database, after "flask --app run db upgrade".
    @app.cli.command('create-admin')
    def create_admin():
        """Create the first admin from ADMIN_EMAIL and ADMIN_PASSWORD."""
        from .models import User
        email = os.environ.get('ADMIN_EMAIL')
        password = os.environ.get('ADMIN_PASSWORD')
        if not (email and password):
            print('Set ADMIN_EMAIL and ADMIN_PASSWORD first.')
            return
        if User.query.filter_by(role='admin').first():
            print('An admin already exists.')
            return
        db.session.add(User(
            username='admin',
            email=email,
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            role='admin',
        ))
        db.session.commit()
        print('Admin created.')

    return app