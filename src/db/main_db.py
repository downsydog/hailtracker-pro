"""
Shared helpers for accessing the MAIN database (hail_events, hail_damage_grid,
hail_swaths).

The main database is:
  - PostgreSQL when DATABASE_URL is set (production / Docker)
  - database/hailtracker_pro.db (SQLite) in local development

The CRM database (data/hailtracker_crm.db) stores leads, customers, jobs, etc.
Hail-domain tables are NOT in the CRM database.

Usage:
    from src.db.main_db import get_main_db, MAIN_DB_PATH

    db = get_main_db()
    events = db.execute("SELECT * FROM hail_events LIMIT 10")
"""

from pathlib import Path

from src.db.database import Database

# Project root: src/db/main_db.py → src/db → src → <project_root>
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MAIN_DB_PATH = str(_PROJECT_ROOT / "database" / "hailtracker_pro.db")


def get_main_db() -> Database:
    """Return a Database instance pointing at the MAIN database.

    In PostgreSQL mode the db_path is ignored (all connections go through the
    central pool), so this helper is safe to call in both PG and SQLite modes.
    """
    return Database(MAIN_DB_PATH)
