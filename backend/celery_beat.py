"""
Celery Beat Startup Script
==========================
Start the Celery Beat scheduler for periodic tasks.

Usage:
    celery -A celery_beat.celery_app beat --loglevel=info
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backend.app import create_app
from backend.app.celery_app import celery_app

# Create Flask app and push context
app = create_app()
app.app_context().push()

if __name__ == '__main__':
    celery_app.Beat().run()
