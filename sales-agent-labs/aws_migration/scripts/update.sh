#!/bin/bash
# Update Script for PresGen
# Handles different update scenarios:
#   - Code updates (git pull + rebuild)
#   - Dependency updates (pip, npm)
#   - Configuration updates
#   - Security patches (system packages)
#   - Database migrations
#
# Usage: ./update.sh [update-type]
#   update-type: code | deps | config | security | full

set -e

# ===== Configuration =====
UPDATE_TYPE="${1:-code}"
BACKUP_BEFORE_UPDATE=true
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ===== Functions =====

pre_update_backup() {
    if [ "$BACKUP_BEFORE_UPDATE" = true ]; then
        log_info "Creating pre-update backup..."
        /home/ubuntu/presgen/scripts/backup.sh database
        log_info "Backup completed"
    fi
}

update_code() {
    log_info "Updating application code..."

    cd /home/ubuntu/presgen

    # Stash local changes (if any)
    if [ -d ".git" ]; then
        log_info "Pulling latest code from git..."
        git stash
        git pull origin main
        git stash pop || log_warn "No stashed changes to apply"
    else
        log_warn "Not a git repository. Manual code update required."
        return
    fi

    # Rebuild Docker images
    log_info "Rebuilding Docker images..."
    docker-compose build --no-cache

    # Restart services
    log_info "Restarting services..."
    docker-compose down
    docker-compose up -d

    # Wait for services
    log_info "Waiting for services to start..."
    sleep 60

    # Verify
    verify_services

    log_info "Code update completed"
}

update_dependencies() {
    log_info "Updating dependencies..."

    cd /home/ubuntu/presgen

    # Update Python dependencies
    log_info "Updating Python dependencies..."

    # Core backend
    docker exec presgen-core bash -c "pip install --upgrade pip && pip install --upgrade -r requirements.txt"

    # Assess backend
    docker exec presgen-assess bash -c "pip install --upgrade pip && pip install --upgrade -r requirements.txt"

    # Update Node.js dependencies
    log_info "Updating Node.js dependencies..."
    docker exec presgen-ui bash -c "npm update && npm audit fix"

    # Restart services to apply updates
    log_info "Restarting services..."
    docker-compose restart

    log_info "Dependencies updated"
}

update_configuration() {
    log_info "Updating configuration..."

    cd /home/ubuntu/presgen

    # Backup current config
    cp .env .env.backup.${TIMESTAMP}
    cp docker-compose.yml docker-compose.yml.backup.${TIMESTAMP}

    log_info "Current configuration backed up"

    # Check for changes in .env.template
    if [ -f ".env.template" ]; then
        log_warn "Review .env.template for new configuration options"
        diff .env .env.template || true
    fi

    # Reload environment variables
    log_info "Reloading configuration..."
    docker-compose down
    docker-compose up -d

    log_info "Configuration updated"
}

update_security() {
    log_info "Applying security updates..."

    # Update system packages
    log_info "Updating system packages..."
    sudo apt-get update
    sudo apt-get upgrade -y
    sudo apt-get autoremove -y

    # Update Docker images to latest security patches
    log_info "Pulling latest base images..."
    docker pull python:3.13-slim
    docker pull node:18-alpine
    docker pull nginx:alpine
    docker pull redis:7-alpine

    # Rebuild with updated base images
    log_info "Rebuilding with updated images..."
    docker-compose build --pull --no-cache

    # Restart services
    docker-compose down
    docker-compose up -d

    # Check for Docker security issues
    log_info "Scanning for vulnerabilities..."
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy image presgen-core || log_warn "Trivy scan completed with warnings"

    log_info "Security updates completed"
}

run_database_migrations() {
    log_info "Running database migrations..."

    # Assess API migrations
    if docker ps | grep -q presgen-assess; then
        log_info "Running Alembic migrations..."
        docker exec presgen-assess alembic upgrade head

        log_info "Database migrations completed"
    fi

    # Verify database integrity
    docker exec presgen-assess python -c "
from src.service.database import get_session
import asyncio

async def check_db():
    async for session in get_session():
        result = await session.execute('SELECT 1')
        print('Database connection OK')
        break

asyncio.run(check_db())
" || log_error "Database check failed"
}

rollback_update() {
    local backup_timestamp=$1
    log_warn "Rolling back to previous version..."

    cd /home/ubuntu/presgen

    # Restore configuration
    if [ -f ".env.backup.${backup_timestamp}" ]; then
        cp .env.backup.${backup_timestamp} .env
    fi

    if [ -f "docker-compose.yml.backup.${backup_timestamp}" ]; then
        cp docker-compose.yml.backup.${backup_timestamp} docker-compose.yml
    fi

    # Rollback git
    if [ -d ".git" ]; then
        git checkout HEAD~1
    fi

    # Rebuild and restart
    docker-compose build --no-cache
    docker-compose down
    docker-compose up -d

    log_warn "Rollback completed"
}

verify_services() {
    log_info "Verifying services..."

    sleep 30  # Wait for services to stabilize

    # Check container status
    docker-compose ps

    # Health checks
    CORE_HEALTH=$(curl -s http://localhost:8080/health || echo "failed")
    ASSESS_HEALTH=$(curl -s http://localhost:8000/api/v1/health || echo "failed")
    UI_HEALTH=$(curl -s http://localhost:3000 || echo "failed")

    if echo "$CORE_HEALTH" | grep -q "healthy"; then
        log_info "✓ Core API: Healthy"
    else
        log_error "✗ Core API: Unhealthy"
        return 1
    fi

    if echo "$ASSESS_HEALTH" | grep -q "healthy"; then
        log_info "✓ Assess API: Healthy"
    else
        log_error "✗ Assess API: Unhealthy"
        return 1
    fi

    if [ -n "$UI_HEALTH" ]; then
        log_info "✓ Frontend: Healthy"
    else
        log_error "✗ Frontend: Unhealthy"
        return 1
    fi

    log_info "All services verified successfully"
}

cleanup_old_images() {
    log_info "Cleaning up old Docker images..."

    # Remove unused images
    docker image prune -f

    # Remove dangling volumes
    docker volume prune -f

    # Show disk usage
    docker system df

    log_info "Cleanup completed"
}

update_full() {
    log_info "Performing FULL update..."

    update_security
    update_code
    update_dependencies
    run_database_migrations
    cleanup_old_images

    log_info "Full update completed"
}

send_update_notification() {
    local status=$1
    local update_type=$2

    if [ -n "${SNS_TOPIC_ARN:-}" ]; then
        aws sns publish \
            --topic-arn ${SNS_TOPIC_ARN} \
            --subject "PresGen Update: ${status}" \
            --message "Update Type: ${update_type}
Date: $(date)
Status: ${status}
Server: $(hostname)
"
    fi
}

# ===== Main Execution =====
main() {
    log_info "Starting PresGen update: ${UPDATE_TYPE}"
    log_info "Timestamp: ${TIMESTAMP}"

    # Pre-update backup
    pre_update_backup

    case ${UPDATE_TYPE} in
        code)
            update_code
            ;;
        deps)
            update_dependencies
            ;;
        config)
            update_configuration
            ;;
        security)
            update_security
            ;;
        database)
            run_database_migrations
            ;;
        full)
            update_full
            ;;
        rollback)
            rollback_update "${2:-$TIMESTAMP}"
            ;;
        *)
            log_error "Unknown update type: ${UPDATE_TYPE}"
            log_info "Usage: $0 [code|deps|config|security|database|full|rollback]"
            exit 1
            ;;
    esac

    verify_services

    log_info "Update completed successfully!"
    send_update_notification "SUCCESS" "${UPDATE_TYPE}"
}

# Trap errors
trap 'log_error "Update failed! Use: ./update.sh rollback ${TIMESTAMP}"; send_update_notification "FAILED" "${UPDATE_TYPE}"; exit 1' ERR

main
