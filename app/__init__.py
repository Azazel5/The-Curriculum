import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
mail = Mail()


def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=True)

    if config_class is None:
        from config import DevelopmentConfig
        config_class = DevelopmentConfig

    app.config.from_object(config_class)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)

    # Register blueprints
    from app.routes.dashboard import dashboard_bp
    from app.routes.curriculum import curriculum_bp
    from app.routes.sessions import sessions_bp
    from app.routes.api import api_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(curriculum_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)

    # API routes don't need CSRF (JS clients use JSON)
    csrf.exempt(api_bp)

    # Jinja2 filters
    @app.template_filter('duration')
    def duration_filter(minutes):
        if not minutes:
            return '0m'
        minutes = int(minutes)
        h, m = divmod(minutes, 60)
        if h and m:
            return f'{h}h {m}m'
        if h:
            return f'{h}h'
        return f'{m}m'

    @app.template_filter('pct_color')
    def pct_color_filter(pct):
        if pct >= 75:
            return '#22c55e'
        if pct >= 25:
            return '#f59e0b'
        return '#ef4444'

    # Register CLI commands
    from app.commands import register_commands
    register_commands(app)

    # Start email reminder scheduler
    if not app.config.get('TESTING'):
        from app.utils.scheduler import start_scheduler
        start_scheduler(app)

    return app
