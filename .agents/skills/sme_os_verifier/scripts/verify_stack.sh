#!/bin/bash

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Stratify System Auditor ===${NC}"

# 1. Database Check
echo -n "Checking SQLite database file... "
if [ -f "backend/sme_platform.db" ]; then
    echo -e "${GREEN}FOUND${NC} (backend/sme_platform.db)"
else
    echo -e "${RED}MISSING${NC} (Database not initialized yet. Start backend server first.)"
fi

# 2. Backend Server Check
echo -n "Checking FastAPI backend server (port 8000)... "
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")

if [ "$BACKEND_STATUS" = "200" ]; then
    echo -e "${GREEN}ONLINE${NC} (health status: OK)"
else
    echo -e "${RED}OFFLINE${NC} (Status: $BACKEND_STATUS. Run backend server to connect.)"
fi

# 3. Frontend Dev Server Check
echo -n "Checking Vite frontend client (port 5173)... "
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/ 2>/dev/null || echo "000")

if [ "$FRONTEND_STATUS" = "200" ] || [ "$FRONTEND_STATUS" = "304" ]; then
    echo -e "${GREEN}ONLINE${NC} (http code: $FRONTEND_STATUS)"
else
    echo -e "${YELLOW}OFFLINE/UNKNOWN${NC} (Status: $FRONTEND_STATUS. Start Vite client dev server.)"
fi

echo -e "${YELLOW}===================================${NC}"
