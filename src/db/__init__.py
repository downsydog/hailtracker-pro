"""
Database module for HailTracker Pro

Central DB engine supports SQLite (default) and PostgreSQL via DATABASE_URL.
"""

from .crm_database import CRMDatabase
from .engine import get_connection, get_engine_info, close_engine, placeholder, is_postgres

__all__ = [
    'CRMDatabase',
    'get_connection',
    'get_engine_info',
    'close_engine',
    'placeholder',
    'is_postgres',
]
