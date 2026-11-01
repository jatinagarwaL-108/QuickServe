import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Project root = the folder that contains run.py, templates/ and static/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

if load_dotenv:
    load_dotenv(os.path.join(BASE_DIR, '.env'))  # local development only


def _database_uri():
    uri = os.environ.get('DATABASE_URL')
    if not uri:
        # Same file the old app.py used
        return 'sqlite:///' + os.path.join(BASE_DIR, 'local_services.db')
    if uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql://', 1)
    return uri


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')  # no default on purpose
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}