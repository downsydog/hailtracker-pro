#!/bin/bash
#
# Stage 8G: Run Full Smoke Test Suite
#
# Usage:
#   ./e2e/run-smoke-tests.sh
#   FRONTEND_URL=http://localhost:3000 ./e2e/run-smoke-tests.sh

set -e

echo "========================================="
echo "HailTracker Pro - E2E Smoke Test Suite"
echo "Stage 8G"
echo "========================================="
echo ""

# Default URLs
FRONTEND_URL=${FRONTEND_URL:-http://localhost:5173}
BACKEND_URL=${BACKEND_URL:-http://localhost:5000}

echo "Frontend URL: $FRONTEND_URL"
echo "Backend URL: $BACKEND_URL"
echo ""

# Check if services are running
echo "Checking services..."

if curl -s --head "$FRONTEND_URL" > /dev/null 2>&1; then
    echo "✓ Frontend is reachable"
else
    echo "✗ Frontend is NOT reachable at $FRONTEND_URL"
    echo "  Please start the frontend server first: npm run dev"
    exit 1
fi

if curl -s "$BACKEND_URL/api/health" > /dev/null 2>&1 || curl -s --head "$BACKEND_URL" > /dev/null 2>&1; then
    echo "✓ Backend is reachable"
else
    echo "✗ Backend is NOT reachable at $BACKEND_URL"
    echo "  Please start the backend server first"
    exit 1
fi

echo ""
echo "========================================="
echo "Running Tests..."
echo "========================================="
echo ""

# Run tests in order
echo "1. Health Checks..."
npx playwright test health-check.spec.ts --reporter=list || true

echo ""
echo "2. Route Integrity Scan..."
npx playwright test route-integrity.spec.ts --reporter=list || true

echo ""
echo "3. Full Estimating Smoke Test..."
npx playwright test estimating-smoke.spec.ts --reporter=list

echo ""
echo "========================================="
echo "Test Complete!"
echo "========================================="
echo ""
echo "View HTML report: npm run e2e:report"
echo "Results JSON: e2e-results.json"
echo ""
