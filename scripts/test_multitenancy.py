#!/usr/bin/env python3
"""
Multi-Tenant Integration Test for HailTracker Pro
Tests all multi-tenant features end-to-end
"""

import requests
import json
import sys

API_BASE = 'http://localhost:5000/api'

# Track test results
passed = 0
failed = 0

def test(name, condition, message=""):
    global passed, failed
    if condition:
        print(f"  [PASS] {name}")
        passed += 1
    else:
        print(f"  [FAIL] {name}: {message}")
        failed += 1

def get(endpoint, headers=None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", headers=headers, timeout=10)
        return r.status_code, r.json()
    except Exception as e:
        return 500, {"error": str(e)}

def post(endpoint, data, headers=None):
    try:
        h = {"Content-Type": "application/json"}
        if headers:
            h.update(headers)
        r = requests.post(f"{API_BASE}{endpoint}", json=data, headers=h, timeout=10)
        return r.status_code, r.json()
    except Exception as e:
        return 500, {"error": str(e)}

def put(endpoint, data, headers=None):
    try:
        h = {"Content-Type": "application/json"}
        if headers:
            h.update(headers)
        r = requests.put(f"{API_BASE}{endpoint}", json=data, headers=h, timeout=10)
        return r.status_code, r.json()
    except Exception as e:
        return 500, {"error": str(e)}


print("=" * 60)
print("HailTracker Pro - Multi-Tenant Integration Test")
print("=" * 60)

# ============================================
# 1. HEALTH CHECK
# ============================================
print("\n1. Health Check")
status, data = get("/health")
test("API health endpoint returns 200", status == 200)
test("Status is 'ok'", data.get("status") == "ok")

# ============================================
# 2. STORMS (SHARED DATA)
# ============================================
print("\n2. Storms (Shared Data - No Tenant Filter)")
status, data = get("/storms?limit=5")
test("Storms endpoint returns 200", status == 200)
test("Total storms > 100,000", data.get("total", 0) > 100000, f"Got {data.get('total', 0)}")
test("Returns storm data", len(data.get("storms", [])) > 0)

# ============================================
# 3. DEV_MODE AUTH
# ============================================
print("\n3. DEV_MODE Authentication")
status, data = get("/auth/me")
test("Auth/me endpoint returns 200", status == 200)
test("DEV_MODE returns admin role", data.get("role") == "admin")
test("DEV_MODE returns tenant_id", data.get("tenant_id") is not None)
test("DEV_MODE returns permissions", len(data.get("permissions", [])) > 0)

# ============================================
# 4. ADMIN STATS
# ============================================
print("\n4. Admin Stats")
status, data = get("/admin/stats")
test("Admin stats endpoint returns 200", status == 200)
test("Returns tenant count", "tenants" in data)
test("Returns user count", "users" in data)
test("Returns storm count", data.get("storms", 0) > 0)
test("System health is ok", data.get("system_health") == "ok")

# ============================================
# 5. TENANT MANAGEMENT
# ============================================
print("\n5. Tenant Management")
status, data = get("/admin/tenants")
test("Tenants endpoint returns 200", status == 200)
test("Returns tenant list", "tenants" in data)
test("Has at least 1 tenant", len(data.get("tenants", [])) >= 1)

# Get first tenant details
if data.get("tenants"):
    tenant_id = data["tenants"][0]["id"]
    status, tenant = get(f"/admin/tenants/{tenant_id}")
    test("Get tenant by ID returns 200", status == 200)
    test("Tenant has company_name", "company_name" in tenant)
    test("Tenant has user_count", "user_count" in tenant)

# ============================================
# 6. USER MANAGEMENT
# ============================================
print("\n6. User Management")
status, data = get("/admin/users")
test("Users endpoint returns 200", status == 200)
test("Returns user list", "users" in data)
test("Has at least 1 user", len(data.get("users", [])) >= 1)

# Check user has required fields
if data.get("users"):
    user = data["users"][0]
    test("User has email", "email" in user)
    test("User has role", "role" in user)
    test("User has tenant_id", "tenant_id" in user)

# ============================================
# 7. ROLE-BASED ACCESS CONTROL
# ============================================
print("\n7. Role-Based Access Control")
status, data = get("/auth/me")
test("DEV_MODE user has admin role", data.get("role") == "admin")
test("Admin has admin:tenants permission", "admin:tenants" in data.get("permissions", []))
test("Admin has admin:users permission", "admin:users" in data.get("permissions", []))

# ============================================
# 8. SUBSCRIPTION PLANS
# ============================================
print("\n8. Subscription Plans")
status, data = get("/admin/plans")
test("Plans endpoint returns 200", status == 200)
test("Returns plans object", "plans" in data)
test("Has free plan", "free" in data.get("plans", {}))
test("Has pro plan", "pro" in data.get("plans", {}))
test("Has enterprise plan", "enterprise" in data.get("plans", {}))

# Check plan details
plans = data.get("plans", {})
if "free" in plans:
    test("Free plan has max_users", plans["free"].get("max_users") == 2)
if "pro" in plans:
    test("Pro plan has max_users", plans["pro"].get("max_users") == 8)
if "enterprise" in plans:
    test("Enterprise has 100 max_users", plans["enterprise"].get("max_users") == 100)

# ============================================
# 9. TENANT PLAN INFO
# ============================================
print("\n9. Tenant Plan Info")
status, data = get("/admin/tenants/1/plan")
test("Tenant plan endpoint returns 200", status == 200)
test("Returns plan name", "plan" in data)
test("Returns usage stats", "usage" in data)
test("Returns dev_mode flag", "dev_mode" in data)

# ============================================
# 10. LEADS (TENANT-SCOPED)
# ============================================
print("\n10. Leads (Tenant-Scoped)")
status, data = get("/leads")
test("Leads endpoint returns 200", status == 200)
test("Returns leads array", "leads" in data)
test("Returns tenant_id in response", "tenant_id" in data)

# ============================================
# 11. JOBS (TENANT-SCOPED)
# ============================================
print("\n11. Jobs (Tenant-Scoped)")
status, data = get("/jobs")
test("Jobs endpoint returns 200", status == 200)
test("Returns jobs array", "jobs" in data)
test("Returns tenant_id in response", "tenant_id" in data)

# ============================================
# 12. API USAGE TRACKING
# ============================================
print("\n12. API Usage Tracking")
status, data = get("/admin/api-usage")
test("API usage endpoint returns 200", status == 200)
test("Returns by_api array", "by_api" in data)
test("Returns daily array", "daily" in data)

# ============================================
# SUMMARY
# ============================================
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    print("\n[WARNING] Some tests failed. Check the output above.")
    sys.exit(1)
else:
    print("\n[SUCCESS] All tests passed! Multi-tenant conversion complete.")
    sys.exit(0)
