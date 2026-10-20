#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default URLs
BASE_URL="${E2E_BASE_URL:-http://127.0.0.1:3000}"
API_URL="${E2E_API_URL:-http://127.0.0.1:8000}"

echo -e "${YELLOW}=== MemoryNest E2E Test Runner ===${NC}"
echo "Base URL: $BASE_URL"
echo "API URL: $API_URL"
echo ""

# Function to check if a service is running
check_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Waiting for $name at $url..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo -e " ${GREEN}OK${NC}"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
        echo -n "."
    done
    echo -e " ${RED}FAILED${NC}"
    return 1
}

# Check if services are running
echo "Checking services..."
check_service "$BASE_URL" "Frontend" || {
    echo -e "${RED}Frontend not running. Start with: npm run dev${NC}"
    exit 1
}

check_service "$API_URL/api/health" "API" || {
    echo -e "${YELLOW}API health endpoint not found, trying root...${NC}"
    check_service "$API_URL" "API" || {
        echo -e "${RED}API not running. Start the backend server.${NC}"
        exit 1
    }
}

echo ""
echo -e "${GREEN}All services running. Starting tests...${NC}"
echo ""

# Run Playwright tests
cd "$(dirname "$0")/.."
npx playwright test e2e/app.spec.ts --reporter=list

