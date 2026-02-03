"""
Test database setup and Flask app.

Run this after starting Docker containers:
    docker-compose up -d
    cd backend
    pip install -r requirements.txt
    python test_setup.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def test_database_connection():
    """Test PostgreSQL connection."""
    print("=" * 60)
    print("TESTING DATABASE CONNECTION")
    print("=" * 60)

    try:
        import psycopg2

        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="hailtracker_master",
            user="hailtracker",
            password="hailtracker_dev_2024"
        )

        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()

        print(f"PostgreSQL connected: {version[0][:50]}...")
        conn.close()
        return True

    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")
        print("\nMake sure Docker is running:")
        print("  docker-compose up -d")
        return False


def test_redis_connection():
    """Test Redis connection."""
    print("\n" + "=" * 60)
    print("TESTING REDIS CONNECTION")
    print("=" * 60)

    try:
        import redis

        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()

        print("Redis connected successfully")
        return True

    except Exception as e:
        print(f"Redis connection failed: {e}")
        return False


def test_flask_app():
    """Test Flask app creation."""
    print("\n" + "=" * 60)
    print("TESTING FLASK APP")
    print("=" * 60)

    try:
        from app import create_app

        app = create_app('development')

        print(f"Flask app created: {app.name}")
        print(f"Debug mode: {app.debug}")
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")

        # List registered blueprints
        print(f"\nRegistered blueprints:")
        for name, bp in app.blueprints.items():
            print(f"  - {name}: {bp.url_prefix}")

        return True

    except Exception as e:
        print(f"Flask app creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_models():
    """Test model imports."""
    print("\n" + "=" * 60)
    print("TESTING MODEL IMPORTS")
    print("=" * 60)

    try:
        from app.models import (
            Storm, Swath, Business, StormBusiness,
            Tenant, Subscription, User, ApiUsage
        )

        models = [Storm, Swath, Business, StormBusiness, Tenant, Subscription, User, ApiUsage]

        print("Master models imported successfully:")
        for model in models:
            print(f"  - {model.__name__}: {model.__tablename__}")

        from app.models.tenant import Lead, Contact, Call, Job, Estimate

        tenant_models = [Lead, Contact, Call, Job, Estimate]

        print("\nTenant models imported successfully:")
        for model in tenant_models:
            print(f"  - {model.__name__}: {model.__tablename__}")

        return True

    except Exception as e:
        print(f"Model import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_tables():
    """Test creating database tables."""
    print("\n" + "=" * 60)
    print("TESTING TABLE CREATION")
    print("=" * 60)

    try:
        from app import create_app
        from app.extensions import db

        app = create_app('development')

        with app.app_context():
            # Create all tables
            db.create_all()

            # Check tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            print(f"Tables created: {len(tables)}")
            for table in sorted(tables):
                print(f"  - {table}")

        return True

    except Exception as e:
        print(f"Table creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("HAILTRACKER PRO - DATABASE SETUP TEST")
    print("=" * 60)
    print()

    results = {
        'PostgreSQL': test_database_connection(),
        'Redis': test_redis_connection(),
        'Flask App': test_flask_app(),
        'Models': test_models(),
    }

    # Only test table creation if database is connected
    if results['PostgreSQL'] and results['Flask App']:
        results['Tables'] = test_create_tables()

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("All tests passed! Database foundation is ready.")
        print("\nNext steps:")
        print("  1. Run: flask db init")
        print("  2. Run: flask db migrate -m 'Initial migration'")
        print("  3. Run: flask db upgrade")
    else:
        print("Some tests failed. Check the errors above.")
        print("\nMake sure Docker is running:")
        print("  docker-compose up -d")

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
