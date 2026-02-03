"""
Celery Worker Startup Script
============================
Start the Celery worker for background task processing.

Usage:
    celery -A celery_worker.celery_app worker --loglevel=info
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.celery_app import celery_app

# Create Flask app and push context
app = create_app()
app.app_context().push()

if __name__ == '__main__':
    celery_app.start()
