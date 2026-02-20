"""
Regression guard: ensure hail-domain SQL never runs against the CRM database.

Tests:
  1. Static analysis — grep code for connection targets that use CRM path
     and then execute hail-domain SQL against them.
  2. Import check — verify src.db.main_db exposes the expected API.

Run:
    python -m pytest tests/test_hail_db_paths.py -v
    # or standalone:
    python tests/test_hail_db_paths.py
"""

import os
import re
import sys
from pathlib import Path

# Allow running as a standalone script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Dangerous patterns: lines where hailtracker_crm.db is used as a connection
# target for hail-domain queries.  These patterns catch:
#   Database('...hailtracker_crm.db')   or   sqlite3.connect('...hailtracker_crm.db')
# followed (nearby) by hail_events / hail_damage_grid / hail_swaths SQL.
#
# We flag lines that assign a db_path default pointing to hailtracker_crm.db
# AND where the same variable is later used to open a connection that runs
# hail-domain SQL.
#
# A simpler heuristic: flag any non-comment line that sets a variable to
# hailtracker_crm.db AND the variable name suggests it will be used for
# hail queries (db_path, hail_db, default param).  Exclude variables
# explicitly named crm_* or that are clearly for CRM tables.
CRM_CONN_RE = re.compile(
    r"""(?:Database|sqlite3\.connect)\s*\(.*hailtracker_crm\.db"""
)
CRM_DEFAULT_RE = re.compile(
    r"""hail_db(?:_path)?\s*=.*hailtracker_crm\.db"""
)

# Directories to scan
SCAN_DIRS = [
    "src/web/routes",
    "src/radar",
    "src/swath",
    "src/business",
    "src/alerts",
    "src/fleet",
    "src/pdr",
    "src/monitoring",
]


def _python_files_in(dirs):
    for rel_dir in dirs:
        d = PROJECT_ROOT / rel_dir
        if not d.is_dir():
            continue
        for py in d.rglob("*.py"):
            yield py


def test_no_crm_connection_for_hail_tables():
    """
    Ensure no code opens Database('...hailtracker_crm.db') or
    sqlite3.connect('...hailtracker_crm.db') and then queries
    hail_events / hail_damage_grid / hail_swaths.

    Heuristic: flag lines matching CRM_CONN_RE or CRM_DEFAULT_RE
    in files that also contain hail-domain SQL, unless the variable
    is explicitly named crm_* (indicating deliberate CRM usage).
    """
    hail_sql_re = re.compile(
        r"\b(?:FROM|INTO|TABLE)\s+(hail_events|hail_damage_grid|hail_swaths)\b",
        re.IGNORECASE,
    )

    violations = []

    for py_file in _python_files_in(SCAN_DIRS):
        text = py_file.read_text(encoding="utf-8", errors="replace")

        if not hail_sql_re.search(text):
            continue  # No hail-domain SQL in this file at all

        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue

            # Check for Database()/sqlite3.connect() with CRM path
            if CRM_CONN_RE.search(line):
                # Allow if variable is explicitly named crm_*
                if re.search(r"crm_db|_CRM_", line):
                    continue
                violations.append(
                    f"{py_file.relative_to(PROJECT_ROOT)}:{lineno}  {stripped.strip()}"
                )

            # Check for db_path/hail_db defaults pointing to CRM
            if CRM_DEFAULT_RE.search(line):
                # Allow if variable is explicitly named crm_*
                if re.search(r"crm_db|_CRM_", line):
                    continue
                violations.append(
                    f"{py_file.relative_to(PROJECT_ROOT)}:{lineno}  {stripped.strip()}"
                )

    msg = (
        "Lines that open a CRM database connection in files with hail-domain SQL.\n"
        "These should use MAIN_DB_PATH or get_main_db() instead:\n  "
        + "\n  ".join(violations)
    )
    assert not violations, msg


def test_main_db_module_api():
    """Verify that src.db.main_db exposes the expected helpers."""
    from src.db.main_db import MAIN_DB_PATH, get_main_db

    assert isinstance(MAIN_DB_PATH, str)
    assert "database" in MAIN_DB_PATH
    assert "hailtracker_pro.db" in MAIN_DB_PATH
    assert "hailtracker_crm" not in MAIN_DB_PATH

    db = get_main_db()
    assert hasattr(db, "execute")
    assert hasattr(db, "get_connection")
    assert "hailtracker_crm" not in db.db_path


def test_main_db_path_is_absolute():
    """MAIN_DB_PATH should be an absolute path to avoid CWD ambiguity."""
    from src.db.main_db import MAIN_DB_PATH

    assert os.path.isabs(MAIN_DB_PATH), (
        f"MAIN_DB_PATH should be absolute, got: {MAIN_DB_PATH}"
    )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("Hail DB Path Regression Guard")
    print("=" * 70)

    passed = 0
    failed = 0

    for name, func in [
        ("no_crm_connection_for_hail_tables", test_no_crm_connection_for_hail_tables),
        ("main_db_module_api", test_main_db_module_api),
        ("main_db_path_is_absolute", test_main_db_path_is_absolute),
    ]:
        try:
            func()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n    {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
