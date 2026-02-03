"""
Celery Test Script
==================
Test Celery worker connectivity and storm processing.

Usage:
    python test_celery.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backend.app import create_app
from backend.app.celery_app import celery_app
from backend.app.tasks.storm_tasks import process_storm
from backend.app.models.master.storm import Storm
from backend.app.extensions import db


def test_celery():
    """Run Celery tests."""
    app = create_app()

    with app.app_context():
        print("=== Testing Celery Setup ===\n")

        # 1. Check Redis connection
        print("1. Checking Redis connection...")
        try:
            result = celery_app.control.ping(timeout=2)
            if result:
                print("   Redis connected! Workers responding.")
            else:
                print("   Redis connected but no workers responding.")
                print("   Start the worker: celery -A celery_worker.celery_app worker --loglevel=info")
        except Exception as e:
            print(f"   Redis error: {e}")
            print("   Make sure Redis is running: docker-compose up -d redis")

        # 2. Check for pending storms
        print("\n2. Checking for pending storms...")
        pending = Storm.query.filter_by(status='pending').first()

        if pending:
            print(f"   Found pending storm: {pending.noaa_id}")
            print(f"   State: {pending.state}")
            print(f"   Event date: {pending.event_date}")
            print(f"\n   To process it, make sure worker is running and use:")
            print(f"   curl -X POST http://localhost:5000/api/admin/storms/{pending.id}/process")
        else:
            print("   No pending storms found")
            print("   You may need to import storm data first")

        # 3. Show storm status summary
        print("\n3. Storm status summary:")
        for status in ['pending', 'processing', 'ready', 'failed', 'expired']:
            count = Storm.query.filter_by(status=status).count()
            print(f"   {status}: {count}")

        # 4. Instructions
        print("\n4. To start the Celery worker:")
        print("   cd backend")
        print("   celery -A celery_worker.celery_app worker --loglevel=info")

        print("\n5. To start Celery Beat (scheduled tasks):")
        print("   cd backend")
        print("   celery -A celery_beat.celery_app beat --loglevel=info")

        print("\n6. To monitor tasks with Flower:")
        print("   docker-compose up -d flower")
        print("   Open http://localhost:5555")

        print("\n7. To process a storm via API:")
        print("   # First get a token")
        print("   curl -X POST http://localhost:5000/api/auth/login \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"email\":\"your@email.com\",\"password\":\"yourpass\"}'")
        print("")
        print("   # Then trigger processing")
        print("   curl -X POST http://localhost:5000/api/admin/storms/1/process \\")
        print("     -H 'Authorization: Bearer YOUR_TOKEN'")

        print("\n=== Celery Setup Complete ===")


if __name__ == '__main__':
    test_celery()
