# HAILTRACKER PRO - MULTI-TENANT CONVERSION STATE
Last updated: 2026-02-03 17:20

## Architecture
- Frontend: frontend/ (React + TypeScript + Vite) - port 5179
- Backend: src/ (Python Flask) - port 5000 via scripts/test_api_server.py
- Database: PostgreSQL on localhost:5432 (hailtracker_master)
- Redis: localhost:6379
- Reference code (DO NOT USE directly): backend/

## Current Database Tables (PostgreSQL hailtracker_master)
- storms: 147,280 rows (SHARED - no tenant scoping needed)
- swaths: 147,280 rows (SHARED - no tenant scoping needed)
- tenants: 2 rows
- users: 2 rows (test@example.com tenant 1, kyle@test.com tenant 2)
- subscriptions: 0 rows
- api_usage: 0 rows
- leads: 0 rows
- contacts: 0 rows
- calls: 0 rows
- jobs: 0 rows
- estimates: 0 rows
- businesses: 0 rows
- storm_businesses: 0 rows

## Existing src/ Structure
- src/auth/ - SQLite-based auth (auth_manager.py, decorators.py, user_model.py) - uses flask_login
- src/api_killswitch.py - API cost protection (KEEP ENABLED)
- src/business/, src/fleet/, src/crm/, src/db/, src/core/, etc.

## Current Backend (scripts/test_api_server.py)
- Has MOCK auth endpoints (login returns fake token, any credentials accepted)
- Connects to PostgreSQL for storms/swaths
- Connects to SQLite for CRM data
- Running on http://localhost:5000

## Completed Tasks
(none yet)

## Current Task
Task 1: JWT Authentication - Backend

## Errors/Blockers
(none yet)

## Notes
- Users table already has: id, tenant_id, email, password_hash (bcrypt), name, phone, role, is_active, last_login, created_at
- Existing users have proper bcrypt hashes
- Need to create REAL JWT auth to replace mock auth in test_api_server.py
