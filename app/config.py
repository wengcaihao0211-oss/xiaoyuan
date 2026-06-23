import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SQLITE_DEV_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'xiaoyuan.db')


def normalize_database_url(url):
    """Normalize DATABASE_URL/SUPABASE_DB_URL for SQLAlchemy."""
    if not url:
        return ''

    normalized = url.strip()
    if normalized.startswith('postgres://'):
        normalized = normalized.replace('postgres://', 'postgresql://', 1)
    return normalized


def resolve_database_url(allow_sqlite=False):
    """Resolve the database URL, preferring Supabase/Postgres."""
    raw_url = os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL', '')
    normalized = normalize_database_url(raw_url)
    if normalized:
        return normalized
    if allow_sqlite:
        return SQLITE_DEV_URI
    return ''


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ITEMS_PER_PAGE = 12
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

    # Upload folder (not used on Vercel / serverless)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = resolve_database_url(
        allow_sqlite=os.getenv('ALLOW_SQLITE_DEV') == '1'
    )
    # 优化连接池配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'pool_timeout': 30,
    }

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = resolve_database_url()
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_recycle': 280,
        'pool_pre_ping': True,
        'pool_timeout': 30,
    }


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
