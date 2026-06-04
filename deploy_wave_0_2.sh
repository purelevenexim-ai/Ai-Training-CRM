#!/bin/bash

# Wave 0.2 Complete - Automated Deployment Script
# Usage: ./deploy_wave_0_2.sh
# This script will:
# 1. Backup the database
# 2. Run the migration
# 3. Restart the server
# 4. Verify deployment

set -e

echo "========================================"
echo "  Wave 0.2 Complete - Deployment Script"
echo "========================================"
echo ""

# Configuration
DB_USER="${DB_USER:-user}"
DB_NAME="${DB_NAME:-pureleven_crm}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_PASSWORD="${DB_PASSWORD}"
APP_DIR="${APP_DIR:/app}"
BACKUP_DIR="${BACKUP_DIR:/backups}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Step 1: Verify prerequisites
print_info "Step 1: Verifying prerequisites..."

if ! command -v alembic &> /dev/null; then
    print_error "alembic not found. Install with: pip install alembic"
fi

if ! command -v psql &> /dev/null; then
    print_error "psql not found. Install PostgreSQL client tools"
fi

if [ ! -d "$APP_DIR" ]; then
    print_error "App directory not found: $APP_DIR"
fi

print_success "All prerequisites met"
echo ""

# Step 2: Backup database
print_info "Step 2: Creating database backup..."

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/pureleven_crm_backup_$(date +%Y%m%d_%H%M%S).sql"

if [ -z "$DB_PASSWORD" ]; then
    print_warning "DB_PASSWORD not set. You may be prompted for password."
    pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" > "$BACKUP_FILE"
else
    PGPASSWORD="$DB_PASSWORD" pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" > "$BACKUP_FILE"
fi

if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    print_success "Database backup created: $BACKUP_FILE ($BACKUP_SIZE)"
else
    print_error "Failed to create database backup"
fi
echo ""

# Step 3: Navigate to app directory
print_info "Step 3: Preparing application..."

cd "$APP_DIR" || print_error "Failed to change directory to $APP_DIR"

# Activate virtual environment if exists
if [ -f ".venv/bin/activate" ]; then
    print_info "Activating virtual environment..."
    source .venv/bin/activate
    print_success "Virtual environment activated"
else
    print_warning "Virtual environment not found. Assuming system Python is configured"
fi
echo ""

# Step 4: Run alembic migration
print_info "Step 4: Running database migration 008..."

export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

# Check current migration version
CURRENT_VERSION=$(alembic current 2>/dev/null || echo "unknown")
print_info "Current migration version: $CURRENT_VERSION"

# Run migration
if alembic upgrade 008; then
    print_success "Migration 008 completed successfully"
else
    print_error "Migration 008 failed. Restoring database from backup..."
    # Restore backup
    if [ -z "$DB_PASSWORD" ]; then
        psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" < "$BACKUP_FILE"
    else
        PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" < "$BACKUP_FILE"
    fi
    print_error "Database restored from backup"
fi

# Verify migration
NEW_VERSION=$(alembic current)
if [[ "$NEW_VERSION" == *"008"* ]]; then
    print_success "Migration verified: $NEW_VERSION"
else
    print_error "Migration verification failed"
fi
echo ""

# Step 5: Verify database changes
print_info "Step 5: Verifying database schema..."

# Check if feature_toggles table exists
if [ -z "$DB_PASSWORD" ]; then
    TABLE_EXISTS=$(psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -t -c "SELECT to_regclass('public.feature_toggles');" 2>/dev/null || echo "null")
else
    TABLE_EXISTS=$(PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -t -c "SELECT to_regclass('public.feature_toggles');" 2>/dev/null || echo "null")
fi

if [ "$TABLE_EXISTS" != "null" ]; then
    print_success "feature_toggles table created successfully"
    
    # Count toggles
    if [ -z "$DB_PASSWORD" ]; then
        TOGGLE_COUNT=$(psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM feature_toggles;" 2>/dev/null || echo "0")
    else
        TOGGLE_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM feature_toggles;" 2>/dev/null || echo "0")
    fi
    print_success "Feature toggles initialized: $TOGGLE_COUNT features"
else
    print_error "feature_toggles table not found. Migration may have failed."
fi
echo ""

# Step 6: Restart FastAPI server
print_info "Step 6: Restarting FastAPI server..."

if command -v supervisorctl &> /dev/null; then
    if supervisorctl restart fastapi 2>/dev/null; then
        print_success "FastAPI restarted via supervisorctl"
        sleep 2
    else
        print_warning "supervisorctl failed. Try manual restart."
    fi
elif command -v systemctl &> /dev/null; then
    if sudo systemctl restart fastapi 2>/dev/null; then
        print_success "FastAPI restarted via systemctl"
        sleep 2
    else
        print_warning "systemctl restart failed. Try manual restart."
    fi
else
    print_warning "Neither supervisorctl nor systemctl found. Please restart FastAPI manually."
fi
echo ""

# Step 7: Verify API endpoints
print_info "Step 7: Verifying API endpoints..."

sleep 2  # Give server time to restart

# Try to reach the features endpoint
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/ai/wave02/features/all 2>/dev/null || echo "000")

if [ "$RESPONSE" = "200" ]; then
    print_success "API endpoints responding correctly"
else
    print_warning "API endpoint returned HTTP $RESPONSE. Server may still be starting."
fi
echo ""

# Summary
echo "========================================"
echo "  Deployment Summary"
echo "========================================"
print_success "Wave 0.2 deployment completed successfully!"
echo ""
echo "Next steps:"
echo "1. Verify all features in admin dashboard"
echo "2. Check logs: tail -f /var/log/fastapi/app.log"
echo "3. Test toggle endpoints: curl http://localhost:8000/api/ai/wave02/features/all"
echo "4. Access admin dashboard: https://your-domain/dashboard"
echo ""
echo "Backup location: $BACKUP_FILE"
echo ""
print_info "Deployment finished at $(date)"
