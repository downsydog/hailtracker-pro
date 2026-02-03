# HAILTRACKER PRO - MULTI-TENANT CONVERSION
# RULE: ALL work in src/. NEVER touch backend/. App must work after every change.

## Task 1: JWT Authentication - Backend [COMPLETE]
- [x] Create src/auth/ folder with: jwt_utils.py, auth_routes.py, auth_middleware.py
- [x] JWT utils: generate_token(), verify_token(), refresh_token()
- [x] Auth routes: POST /api/auth/login, POST /api/auth/register, POST /api/auth/refresh, GET /api/auth/me
- [x] Auth middleware: decorator that checks JWT token on protected routes
- [x] Add DEV_MODE=true bypass so app works without login during development
- [x] Register auth routes in scripts/test_api_server.py
- [x] Hash passwords with bcrypt
- [x] Test: register, login, /me, storms still work, health still returns ok
- [x] Git commit
- [x] Update STATE.md

## Task 2: JWT Authentication - Frontend [COMPLETE]
- [x] Create login page at frontend/src/pages/auth/login.tsx (already existed)
- [x] Create register page at frontend/src/pages/auth/register.tsx (already existed)
- [x] Create auth context/provider that stores JWT token
- [x] Add token to all API requests via interceptor (already in client.ts)
- [x] Route protection: redirect to login if no token (ProtectedRoute.tsx)
- [x] DEV_MODE bypass on frontend (auto-login as dev user)
- [x] Logout button in sidebar/topbar (UserMenu.tsx)
- [x] Test: register, login, existing pages still work, logout works, DEV_MODE skips login
- [x] Git commit
- [x] Update STATE.md

## Task 3: Tenant Scoping - Database [COMPLETE]
- [x] Add tenant_id column to tables that need it: leads, contacts, calls, jobs, estimates, businesses, api_usage
- [x] Tables that are SHARED (no tenant_id): storms, swaths
- [x] Set tenant_id = 1 for all existing data (DEFAULT 1 on column)
- [x] DO NOT drop or recreate any tables. Only ALTER existing ones.
- [x] Verify: storms still returns 147,280, all data preserved
- [x] Git commit
- [x] Update STATE.md

## Task 4: Tenant Scoping - Backend Queries
- [ ] Create src/auth/tenant_context.py - gets current tenant from JWT
- [ ] Modify queries: shared data (storms, swaths) = no filter, private data (leads, jobs) = filter by tenant_id
- [ ] In DEV_MODE default to tenant_id = 1
- [ ] Test: storms returns all, leads returns only tenant 1, app works end to end
- [ ] Git commit
- [ ] Update STATE.md

## Task 5: Role-Based Access Control
- [ ] Add role column to users: admin, manager, technician, viewer
- [ ] Kyle = admin
- [ ] Create src/auth/permissions.py with @require_role decorator
- [ ] Admin: full access. Manager: leads/jobs/estimates. Technician: assigned jobs. Viewer: read-only.
- [ ] DEV_MODE defaults to admin
- [ ] Test: admin accesses all, technician blocked from admin routes, DEV_MODE works
- [ ] Git commit
- [ ] Update STATE.md

## Task 6: Admin Portal Backend
- [ ] Create src/admin/admin_routes.py
- [ ] Routes: GET/POST /api/admin/tenants, GET/PUT /api/admin/tenants/:id, GET/POST /api/admin/users, GET /api/admin/stats, GET /api/admin/api-usage
- [ ] All require @require_role('admin')
- [ ] Register in scripts/test_api_server.py
- [ ] Test: each endpoint with admin token, non-admin gets 403
- [ ] Git commit
- [ ] Update STATE.md

## Task 7: Admin Portal Frontend
- [ ] Review existing frontend/src/apps/admin/ pages - keep what works, fix what's broken
- [ ] Dashboard: tenant count, user count, storm count, system health
- [ ] Tenant management: list, create/edit, set plan
- [ ] User management: list, create, assign role and tenant
- [ ] Connect to src/admin/ routes
- [ ] Only visible to admin role
- [ ] Test: login as admin, see real data, original pages still work
- [ ] Git commit
- [ ] Update STATE.md

## Task 8: Subscription Plans and Limits
- [ ] Create src/billing/plans.py: free (2 users, 3 storms/mo), pro (8 users, 50 storms/mo, $99), enterprise (100 users, unlimited, $299)
- [ ] Plan enforcement middleware
- [ ] Track usage per tenant per month
- [ ] 403 with upgrade message when limit exceeded
- [ ] DEV_MODE = enterprise (no limits)
- [ ] Test: free plan hits limit, enterprise no limit, DEV_MODE no limit
- [ ] Git commit
- [ ] Update STATE.md

## Task 9: Final Integration Test
- [ ] Start backend and frontend
- [ ] Register new user, login, verify storms show on map
- [ ] Verify tenant scoping, admin portal, role-based access
- [ ] npm run build compiles clean
- [ ] Create scripts/test_multitenancy.py that tests everything
- [ ] Git commit "Multi-tenant conversion complete"
- [ ] Update STATE.md with final status
