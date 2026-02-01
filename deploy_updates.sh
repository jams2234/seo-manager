#!/bin/bash
# SEO Analyzer - Deploy Updates Script
# Celery Worker 재시작 + Frontend 빌드 및 배포를 한번에 실행

set -e  # Exit on error

echo "======================================"
echo "SEO Analyzer - Deploying Updates"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="/root/telegram_bot"

# Step 1: Stop Celery Workers
echo -e "${YELLOW}[1/6] Stopping Celery Workers...${NC}"
pkill -9 -f "celery.*worker" 2>/dev/null || echo "No Celery workers running"
sleep 2
echo -e "${GREEN}✓ Celery workers stopped${NC}"
echo ""

# Step 2: Build React Frontend
echo -e "${YELLOW}[2/6] Building React Frontend...${NC}"
cd "$PROJECT_ROOT/frontend"
npm run build
echo -e "${GREEN}✓ Frontend built successfully${NC}"
echo ""

# Step 3: Copy frontend build to static directory
echo -e "${YELLOW}[3/6] Copying frontend build to static directory...${NC}"

# Copy JS files to static/js (where Nginx expects them)
echo "  Copying JS files..."
mkdir -p "$PROJECT_ROOT/static/js"
cp -f "$PROJECT_ROOT/frontend/build/static/js/"* "$PROJECT_ROOT/static/js/" 2>/dev/null || echo "  No JS files to copy"

# Copy CSS files to static/css (where Nginx expects them)
echo "  Copying CSS files..."
mkdir -p "$PROJECT_ROOT/static/css"
cp -f "$PROJECT_ROOT/frontend/build/static/css/"* "$PROJECT_ROOT/static/css/" 2>/dev/null || echo "  No CSS files to copy"

# Copy entire build to static/frontend (for reference/backup)
echo "  Copying complete build to static/frontend..."
rm -rf "$PROJECT_ROOT/static/frontend"
mkdir -p "$PROJECT_ROOT/static/frontend"
cp -r "$PROJECT_ROOT/frontend/build/"* "$PROJECT_ROOT/static/frontend/"

echo -e "${GREEN}✓ Frontend files copied to static directory${NC}"
echo ""

# Step 4: Run database migrations
echo -e "${YELLOW}[4/7] Running database migrations...${NC}"
cd "$PROJECT_ROOT"
python3 manage.py migrate --noinput
echo -e "${GREEN}✓ Migrations completed${NC}"
echo ""

# Step 5: Collect static files
echo -e "${YELLOW}[5/7] Collecting static files...${NC}"
cd "$PROJECT_ROOT"
python3 manage.py collectstatic --noinput
echo -e "${GREEN}✓ Static files collected${NC}"
echo ""

# Step 6: Restart services (applies backend code changes)
echo -e "${YELLOW}[6/7] Restarting services...${NC}"
echo "  Restarting uWSGI (applies Python/Django code changes)..."
sudo systemctl restart uwsgi
echo "  Reloading Nginx (applies frontend changes)..."
sudo nginx -s reload
echo -e "${GREEN}✓ uWSGI and Nginx restarted${NC}"
echo ""

# Step 7: Start Celery Worker
echo -e "${YELLOW}[7/7] Starting Celery Worker...${NC}"
cd "$PROJECT_ROOT"
# Using solo pool to avoid SIGABRT crashes with Google API C libraries (SSL/gRPC)
nohup python3 -m celery -A telegram_bot worker -l info --pool=solo --logfile=/tmp/celery_worker.log > /tmp/celery_worker_startup.log 2>&1 &
sleep 3

# Verify Celery is running
if pgrep -f "celery.*worker" > /dev/null; then
    WORKER_COUNT=$(pgrep -f "celery.*worker" | wc -l)
    echo -e "${GREEN}✓ Celery worker started ($WORKER_COUNT processes)${NC}"
else
    echo -e "${RED}✗ Failed to start Celery worker${NC}"
    echo "Check logs: tail -50 /tmp/celery_worker.log"
    exit 1
fi
echo ""

# Summary
echo "======================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "======================================"
echo ""
echo "Services Status:"
echo "  - uWSGI: $(sudo systemctl is-active uwsgi)"
echo "  - Nginx: $(sudo systemctl is-active nginx)"
echo "  - Celery Worker: Running ($WORKER_COUNT processes)"
echo ""
echo "Logs:"
echo "  - Celery Worker: tail -f /tmp/celery_worker.log"
echo "  - uWSGI: sudo journalctl -u uwsgi -f"
echo "  - Nginx: sudo tail -f /var/log/nginx/error.log"
echo ""
echo "Test your changes at: https://coingry.shop"
echo ""
