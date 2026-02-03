import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Master database (shared data: storms, businesses, tenants, users)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'MASTER_DATABASE_URL',
        'postgresql://hailtracker:hailtracker_dev_2024@localhost:5432/hailtracker_master'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
    }

    # Tenant database template
    TENANT_DB_TEMPLATE = os.getenv(
        'TENANT_DB_TEMPLATE',
        'postgresql://hailtracker:hailtracker_dev_2024@localhost:5432/tenant_{tenant_id}'
    )

    # JWT settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # Celery
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')

    # Business data retention
    BUSINESS_DATA_RETENTION_DAYS = 29

    # API Keys (from existing .env)
    YELP_API_KEY = os.getenv('YELP_API_KEY')
    HERE_API_KEY = os.getenv('HERE_API_KEY')
    TOMTOM_API_KEY = os.getenv('TOMTOM_API_KEY')
    GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')
    FOURSQUARE_API_KEY = os.getenv('FOURSQUARE_API_KEY')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
