#!/bin/bash
# Monitoring Script for PresGen
# Real-time dashboard showing:
#   - Service health status
#   - Resource usage (CPU, memory, disk)
#   - Active workflows
#   - Recent errors
#   - Request metrics
#
# Usage: ./monitor.sh [mode]
#   mode: dashboard | logs | metrics | health | errors

set -e

MODE="${1:-dashboard}"
REFRESH_INTERVAL=30  # seconds

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ===== Functions =====

check_service_health() {
    echo -e "${CYAN}=== SERVICE HEALTH ===${NC}"

    # Core API
    CORE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null || echo "000")
    if [ "$CORE_STATUS" = "200" ]; then
        echo -e "Core API (8080):       ${GREEN}✓ Healthy${NC}"
    else
        echo -e "Core API (8080):       ${RED}✗ Down (HTTP $CORE_STATUS)${NC}"
    fi

    # Assess API
    ASSESS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health 2>/dev/null || echo "000")
    if [ "$ASSESS_STATUS" = "200" ]; then
        echo -e "Assess API (8000):     ${GREEN}✓ Healthy${NC}"
    else
        echo -e "Assess API (8000):     ${RED}✗ Down (HTTP $ASSESS_STATUS)${NC}"
    fi

    # Frontend
    UI_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "000")
    if [ "$UI_STATUS" = "200" ]; then
        echo -e "Frontend (3000):       ${GREEN}✓ Healthy${NC}"
    else
        echo -e "Frontend (3000):       ${RED}✗ Down (HTTP $UI_STATUS)${NC}"
    fi

    # Redis
    REDIS_STATUS=$(docker exec presgen-redis redis-cli ping 2>/dev/null || echo "FAILED")
    if [ "$REDIS_STATUS" = "PONG" ]; then
        echo -e "Redis:                 ${GREEN}✓ Healthy${NC}"
    else
        echo -e "Redis:                 ${RED}✗ Down${NC}"
    fi

    # Database
    if docker ps | grep -q presgen-postgres; then
        POSTGRES_STATUS=$(docker exec presgen-postgres pg_isready -U presgen 2>/dev/null || echo "failed")
        if echo "$POSTGRES_STATUS" | grep -q "accepting connections"; then
            echo -e "PostgreSQL:            ${GREEN}✓ Healthy${NC}"
        else
            echo -e "PostgreSQL:            ${RED}✗ Down${NC}"
        fi
    else
        echo -e "Database (SQLite):     ${GREEN}✓ File-based${NC}"
    fi

    # nginx
    NGINX_STATUS=$(docker ps --filter "name=presgen-nginx" --format "{{.Status}}" | grep -q "Up" && echo "Up" || echo "Down")
    if [ "$NGINX_STATUS" = "Up" ]; then
        echo -e "nginx:                 ${GREEN}✓ Running${NC}"
    else
        echo -e "nginx:                 ${RED}✗ Down${NC}"
    fi

    echo ""
}

show_resource_usage() {
    echo -e "${CYAN}=== RESOURCE USAGE ===${NC}"

    # System resources
    echo "System Resources:"
    free -h | grep -E "Mem:|Swap:"
    echo ""

    # Disk usage
    echo "Disk Usage:"
    df -h | grep -E "Filesystem|/dev/root"
    echo ""

    # Docker resources
    echo "Container Resources:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
    echo ""

    # Check thresholds
    MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    DISK_USAGE=$(df -h | grep /dev/root | awk '{print $5}' | tr -d '%')

    if [ "$MEM_USAGE" -gt 80 ]; then
        echo -e "${RED}⚠ WARNING: Memory usage at ${MEM_USAGE}%${NC}"
    fi

    if [ "$DISK_USAGE" -gt 80 ]; then
        echo -e "${RED}⚠ WARNING: Disk usage at ${DISK_USAGE}%${NC}"
    fi

    echo ""
}

show_active_workflows() {
    echo -e "${CYAN}=== ACTIVE WORKFLOWS ===${NC}"

    # Query Assess API for active workflows
    WORKFLOWS=$(curl -s http://localhost:8000/api/v1/workflows?status=running 2>/dev/null || echo "[]")

    if [ "$WORKFLOWS" = "[]" ]; then
        echo "No active workflows"
    else
        echo "$WORKFLOWS" | jq -r '.[] | "\(.id) - Step \(.current_step)/11 (\(.current_step_name))"' 2>/dev/null || echo "Error parsing workflows"
    fi

    echo ""
}

show_recent_errors() {
    echo -e "${CYAN}=== RECENT ERRORS (last 10 minutes) ===${NC}"

    # Get errors from all containers
    docker-compose logs --since=10m 2>/dev/null | grep -i error | tail -20 || echo "No recent errors"

    echo ""
}

show_request_metrics() {
    echo -e "${CYAN}=== REQUEST METRICS (last hour) ===${NC}"

    # Parse nginx access logs
    if [ -f "/var/log/nginx/access.log" ]; then
        echo "Top Endpoints:"
        tail -1000 /var/log/nginx/access.log | \
            awk '{print $7}' | sort | uniq -c | sort -rn | head -10

        echo ""
        echo "Status Codes:"
        tail -1000 /var/log/nginx/access.log | \
            awk '{print $9}' | sort | uniq -c | sort -rn

        echo ""
        echo "Average Response Time:"
        tail -1000 /var/log/nginx/access.log | \
            awk '{if ($NF ~ /rt=/) print $NF}' | \
            sed 's/rt=//' | \
            awk '{sum+=$1; count++} END {if (count>0) print sum/count "s"; else print "N/A"}'
    else
        echo "nginx logs not available"
    fi

    echo ""
}

show_container_logs() {
    local container=$1
    local lines=${2:-50}

    echo -e "${CYAN}=== LOGS: ${container} (last ${lines} lines) ===${NC}"
    docker logs --tail=${lines} ${container} 2>&1 || echo "Container not found"
    echo ""
}

check_alerts() {
    echo -e "${CYAN}=== ACTIVE ALERTS ===${NC}"

    local alerts=0

    # Memory check
    MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    if [ "$MEM_USAGE" -gt 90 ]; then
        echo -e "${RED}🚨 CRITICAL: Memory usage at ${MEM_USAGE}%${NC}"
        alerts=$((alerts + 1))
    elif [ "$MEM_USAGE" -gt 80 ]; then
        echo -e "${YELLOW}⚠  WARNING: Memory usage at ${MEM_USAGE}%${NC}"
        alerts=$((alerts + 1))
    fi

    # Disk check
    DISK_USAGE=$(df -h | grep /dev/root | awk '{print $5}' | tr -d '%')
    if [ "$DISK_USAGE" -gt 90 ]; then
        echo -e "${RED}🚨 CRITICAL: Disk usage at ${DISK_USAGE}%${NC}"
        alerts=$((alerts + 1))
    elif [ "$DISK_USAGE" -gt 80 ]; then
        echo -e "${YELLOW}⚠  WARNING: Disk usage at ${DISK_USAGE}%${NC}"
        alerts=$((alerts + 1))
    fi

    # CPU check (load average)
    LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    CPU_COUNT=$(nproc)
    if (( $(echo "$LOAD > $CPU_COUNT * 2" | bc -l) )); then
        echo -e "${RED}🚨 CRITICAL: Load average ${LOAD} (${CPU_COUNT} CPUs)${NC}"
        alerts=$((alerts + 1))
    fi

    # Service health checks
    if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${RED}🚨 CRITICAL: Core API is down${NC}"
        alerts=$((alerts + 1))
    fi

    if ! curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo -e "${RED}🚨 CRITICAL: Assess API is down${NC}"
        alerts=$((alerts + 1))
    fi

    # Container status
    STOPPED_CONTAINERS=$(docker ps -a --filter "status=exited" --filter "name=presgen" --format "{{.Names}}")
    if [ -n "$STOPPED_CONTAINERS" ]; then
        echo -e "${RED}🚨 CRITICAL: Stopped containers: $STOPPED_CONTAINERS${NC}"
        alerts=$((alerts + 1))
    fi

    # Error rate check
    ERROR_COUNT=$(docker-compose logs --since=10m 2>/dev/null | grep -i error | wc -l)
    if [ "$ERROR_COUNT" -gt 50 ]; then
        echo -e "${RED}🚨 CRITICAL: ${ERROR_COUNT} errors in last 10 minutes${NC}"
        alerts=$((alerts + 1))
    elif [ "$ERROR_COUNT" -gt 10 ]; then
        echo -e "${YELLOW}⚠  WARNING: ${ERROR_COUNT} errors in last 10 minutes${NC}"
        alerts=$((alerts + 1))
    fi

    if [ "$alerts" -eq 0 ]; then
        echo -e "${GREEN}✓ No active alerts${NC}"
    fi

    echo ""
}

export_metrics() {
    local output_file="/tmp/presgen-metrics-$(date +%Y%m%d_%H%M%S).json"

    cat > ${output_file} <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "hostname": "$(hostname)",
  "system": {
    "memory_usage_percent": $(free | grep Mem | awk '{print int($3/$2 * 100)}'),
    "disk_usage_percent": $(df -h | grep /dev/root | awk '{print $5}' | tr -d '%'),
    "load_average": "$(uptime | awk -F'load average:' '{print $2}' | xargs)"
  },
  "services": {
    "core_api": "$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null || echo 000)",
    "assess_api": "$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health 2>/dev/null || echo 000)",
    "frontend": "$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo 000)"
  },
  "containers": $(docker stats --no-stream --format '{"name":"{{.Name}}","cpu":"{{.CPUPerc}}","memory":"{{.MemPerc}}"}' | jq -s .)
}
EOF

    echo "Metrics exported to: ${output_file}"

    # Upload to S3 if configured
    if [ -n "${S3_BUCKET:-}" ]; then
        aws s3 cp ${output_file} s3://${S3_BUCKET}/metrics/ 2>/dev/null && \
            echo "Metrics uploaded to S3"
    fi
}

dashboard() {
    while true; do
        clear
        echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║          PresGen Monitoring Dashboard                         ║${NC}"
        echo -e "${BLUE}║          $(date '+%Y-%m-%d %H:%M:%S')                                 ║${NC}"
        echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
        echo ""

        check_service_health
        show_resource_usage
        show_active_workflows
        check_alerts
        show_recent_errors

        echo -e "${CYAN}Refreshing in ${REFRESH_INTERVAL} seconds... (Ctrl+C to exit)${NC}"
        sleep ${REFRESH_INTERVAL}
    done
}

# ===== Main Execution =====
main() {
    case ${MODE} in
        dashboard)
            dashboard
            ;;
        health)
            check_service_health
            ;;
        resources)
            show_resource_usage
            ;;
        workflows)
            show_active_workflows
            ;;
        errors)
            show_recent_errors
            ;;
        metrics)
            show_request_metrics
            ;;
        alerts)
            check_alerts
            ;;
        export)
            export_metrics
            ;;
        logs)
            show_container_logs "${2:-presgen-core}" "${3:-50}"
            ;;
        *)
            log_error "Unknown mode: ${MODE}"
            echo "Usage: $0 [dashboard|health|resources|workflows|errors|metrics|alerts|export|logs]"
            exit 1
            ;;
    esac
}

main
