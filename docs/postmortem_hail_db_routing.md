# Postmortem: Hail-Domain DB Routing Bug

**Date:** 2026-02-20
**Commit:** f1d3028
**Severity:** High (all hail endpoints broken in SQLite mode)

## What Broke

Hail-domain tables (`hail_events`, `hail_damage_grid`, `hail_swaths`) live in the
**main database** (`database/hailtracker_pro.db` in SQLite, or the shared PostgreSQL
database in Docker). However, 9 source files across routes and backend services
were opening `Database('data/hailtracker_crm.db')` — the **CRM database** — and
then running SQL against those hail tables.

Affected endpoints included `/api/hail-events/calendar`, heatmap, damage-grid,
fleet location hail overlays, and territory alert storm checks. All returned
`sqlite3.OperationalError: no such table: hail_events` when running locally.

## Why PostgreSQL Masked It

In Docker (production), `DATABASE_URL` is set, so `Database.get_connection()`
ignores the `db_path` argument entirely and returns a connection from the shared
PostgreSQL pool. All tables — CRM and hail — coexist in the same PG database.
The wrong `db_path` was silently ignored, so the bug only surfaced in **SQLite
mode** (local development).

## How We Fixed It

1. **Created `src/db/main_db.py`** — a single shared module exposing:
   - `MAIN_DB_PATH`: absolute path to `database/hailtracker_pro.db`
   - `get_main_db()`: returns a `Database` instance for hail-domain queries

2. **Updated 11 files** to import from `main_db` instead of hardcoding
   `'data/hailtracker_crm.db'`:
   - `src/web/routes/hail_events_api.py` (7 instances)
   - `src/web/routes/fleet_locations_api.py` (4 instances + PG/SQLite branching)
   - `src/web/routes/territory_alerts_api.py` (split cross-DB JOIN for SQLite)
   - `src/radar/damage_grid.py` (3 function defaults)
   - `src/radar/event_persister.py` (1 default)
   - `src/radar/swath_database.py` (constructor default)
   - `src/radar/event_footprint.py` (1 default)
   - `src/swath/intelligence_engine.py` (1 default)
   - `src/business/swath_discovery.py` (added `hail_db_path` param)
   - `src/alerts/storm_monitor.py` (event footprint call)

3. **Fixed `datetime.date` JSON serialization** — PostgreSQL returns
   `datetime.date` objects for `event_date`; added `str()` conversions where
   these values are used as JSON dict keys.

4. **Added regression guard** (`tests/test_hail_db_paths.py`):
   - Static analysis scan: flags `Database()`/`sqlite3.connect()` calls using
     CRM path in files that also contain hail-domain SQL
   - Import check: verifies `main_db` module API and path correctness
   - Path check: ensures `MAIN_DB_PATH` is absolute

## How to Avoid This Going Forward

1. **Always use `get_main_db()` or `MAIN_DB_PATH`** for any query touching
   `hail_events`, `hail_damage_grid`, or `hail_swaths`. Never hardcode a
   database path.

2. **Run `pytest tests/test_hail_db_paths.py`** before merging — it will catch
   any new code that opens a CRM connection in a file with hail-domain SQL.

3. **Test in SQLite mode**, not just Docker/PG. The PG pool silently ignores
   `db_path`, so wrong paths only break locally. A quick
   `unset DATABASE_URL && python -c "from src.db.main_db import get_main_db; ..."`
   will surface routing mistakes immediately.

4. **Know which tables live where:**
   - **Main DB** (`database/hailtracker_pro.db`): `hail_events`,
     `hail_damage_grid`, `hail_swaths`
   - **CRM DB** (`data/hailtracker_crm.db`): `leads`, `customers`, `jobs`,
     `vehicles`, `user_territories`, `territory_alerts`, `fleet_locations`,
     `swath_businesses`
