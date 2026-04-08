import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


def _normalize_database_url(url):
    """Heroku / some hosts used postgres://; SQLAlchemy expects postgresql://."""
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql://', 1)
    return url


def _database_uri():
    url = os.environ.get('DATABASE_URL')
    if not url:
        return 'sqlite:///' + os.path.join(basedir, 'instance', 'curriculum.db')
    return _normalize_database_url(url)


def _engine_options(uri):
    if uri.startswith('sqlite'):
        return {'connect_args': {'check_same_thread': False}}
    # Neon / Render Postgres: pool_pre_ping avoids stale connections after idle.
    return {'pool_pre_ping': True}


_db_uri = _database_uri()
_db_engine_options = _engine_options(_db_uri)


class Config:
    """Base settings. Subclasses set DEBUG and SECRET_KEY policy."""

    SQLALCHEMY_DATABASE_URI = _db_uri
    SQLALCHEMY_ENGINE_OPTIONS = _db_engine_options
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod-please')


class ProductionConfig(Config):
    DEBUG = False
    # Set SECRET_KEY in Render — required for cookies / CSRF; generate a long random string.
    SECRET_KEY = os.environ.get('SECRET_KEY', '')
