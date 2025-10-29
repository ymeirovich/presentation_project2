#!/bin/bash
# Scaling Script for PresGen
# Handles vertical and horizontal scaling:
#   - Vertical: Upgrade/downgrade Lightsail instance size
#   - Horizontal: Add/remove service replicas (future)
#   - Auto-scale: Based on metrics
#
# Usage: ./scale.sh [action] [parameters]
#   action: up | down | auto | status

set -e

ACTION="${1:-status}"
INSTANCE_NAME="${INSTANCE_NAME:-presgen-demo}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ===== Functions =====

get_current_bundle() {
    aws lightsail get-instance \
        --instance-name ${INSTANCE_NAME} \
        --query 'instance.bundleId' \
        --output text
}

show_scaling_status() {
    log_info "Current Scaling Status"
    echo ""

    # Get instance info
    INSTANCE_INFO=$(aws lightsail get-instance --instance-name ${INSTANCE_NAME})

    CURRENT_BUNDLE=$(echo $INSTANCE_INFO | jq -r '.instance.bundleId')
    CURRENT_STATE=$(echo $INSTANCE_INFO | jq -r '.instance.state.name')
    RAM=$(echo $INSTANCE_INFO | jq -r '.instance.hardware.ramSizeInGb')
    CPU=$(echo $INSTANCE_INFO | jq -r '.instance.hardware.cpuCount')
    DISK=$(echo $INSTANCE_INFO | jq -r '.instance.hardware.disksGb[0]')

    echo "Instance: ${INSTANCE_NAME}"
    echo "Bundle: ${CURRENT_BUNDLE}"
    echo "State: ${CURRENT_STATE}"
    echo "Resources: ${RAM}GB RAM, ${CPU} vCPU, ${DISK}GB Disk"
    echo ""

    # Show current resource usage
    log_info "Current Resource Usage:"
    STATIC_IP=$(aws lightsail get-static-ip --static-ip-name ${INSTANCE_NAME}-ip --query 'staticIp.ipAddress' --output text)

    if [ "$CURRENT_STATE" = "running" ]; then
        ssh -i lightsail-key.pem ubuntu@${STATIC_IP} << 'ENDSSH'
            echo "Memory Usage:"
            free -h | grep -E "Mem:"

            echo ""
            echo "CPU Load:"
            uptime

            echo ""
            echo "Disk Usage:"
            df -h | grep -E "/dev/root"

            echo ""
            echo "Container Resources:"
            docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
ENDSSH
    fi

    echo ""
    log_info "Available Bundles:"
    echo "  nano_2_0:   512MB RAM, 1 vCPU, 20GB SSD - $3.50/month"
    echo "  micro_2_0:  1GB RAM, 1 vCPU, 40GB SSD - $5/month"
    echo "  small_2_0:  2GB RAM, 1 vCPU, 60GB SSD - $10/month"
    echo "  medium_2_0: 4GB RAM, 2 vCPU, 80GB SSD - $20/month"
    echo "  large_2_0:  8GB RAM, 2 vCPU, 160GB SSD - $40/month"
}

scale_up() {
    local target_bundle=$1

    log_info "Scaling UP to bundle: ${target_bundle}"

    # Validate bundle
    case ${target_bundle} in
        micro_2_0|small_2_0|medium_2_0|large_2_0|xlarge_2_0)
            ;;
        *)
            log_error "Invalid bundle: ${target_bundle}"
            echo "Valid bundles: micro_2_0, small_2_0, medium_2_0, large_2_0, xlarge_2_0"
            exit 1
            ;;
    esac

    # Create pre-scaling snapshot
    log_warn "Creating pre-scaling snapshot..."
    SNAPSHOT_NAME="${INSTANCE_NAME}-before-scale-$(date +%Y%m%d_%H%M%S)"
    aws lightsail create-instance-snapshot \
        --instance-name ${INSTANCE_NAME} \
        --instance-snapshot-name ${SNAPSHOT_NAME}

    log_info "Snapshot created: ${SNAPSHOT_NAME}"

    # Stop instance
    log_info "Stopping instance..."
    aws lightsail stop-instance --instance-name ${INSTANCE_NAME}
    aws lightsail wait instance-stopped --instance-name ${INSTANCE_NAME}

    # Upgrade bundle
    log_info "Upgrading instance bundle..."
    aws lightsail update-instance-bundle \
        --instance-name ${INSTANCE_NAME} \
        --bundle-id ${target_bundle}

    # Start instance
    log_info "Starting instance..."
    aws lightsail start-instance --instance-name ${INSTANCE_NAME}
    aws lightsail wait instance-running --instance-name ${INSTANCE_NAME}

    log_info "Instance scaled up successfully!"
    log_info "Waiting for services to start..."
    sleep 60

    # Verify services
    verify_services_after_scaling
}

scale_down() {
    local target_bundle=$1

    log_warn "Scaling DOWN to bundle: ${target_bundle}"
    log_warn "WARNING: Scaling down may cause service disruption if resources are tight!"
    read -p "Continue? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Scaling cancelled"
        exit 0
    fi

    # Same process as scale_up
    scale_up ${target_bundle}
}

auto_scale() {
    log_info "Checking auto-scaling conditions..."

    # Get current metrics
    STATIC_IP=$(aws lightsail get-static-ip --static-ip-name ${INSTANCE_NAME}-ip --query 'staticIp.ipAddress' --output text)

    METRICS=$(ssh -i lightsail-key.pem ubuntu@${STATIC_IP} << 'ENDSSH'
        MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
        DISK_USAGE=$(df -h | grep /dev/root | awk '{print $5}' | tr -d '%')
        CPU_LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
        echo "${MEM_USAGE},${DISK_USAGE},${CPU_LOAD}"
ENDSSH
)

    IFS=',' read -r MEM_USAGE DISK_USAGE CPU_LOAD <<< "$METRICS"

    log_info "Current Metrics:"
    log_info "  Memory: ${MEM_USAGE}%"
    log_info "  Disk: ${DISK_USAGE}%"
    log_info "  CPU Load: ${CPU_LOAD}"

    CURRENT_BUNDLE=$(get_current_bundle)

    # Auto-scaling logic
    if [ "$MEM_USAGE" -gt 85 ] || [ "$DISK_USAGE" -gt 85 ]; then
        log_warn "High resource usage detected!"

        case ${CURRENT_BUNDLE} in
            micro_2_0)
                log_info "Recommending scale up to: small_2_0 (2GB RAM)"
                scale_up small_2_0
                ;;
            small_2_0)
                log_info "Recommending scale up to: medium_2_0 (4GB RAM)"
                scale_up medium_2_0
                ;;
            medium_2_0)
                log_info "Recommending scale up to: large_2_0 (8GB RAM)"
                scale_up large_2_0
                ;;
            *)
                log_warn "Already at maximum recommended size or higher"
                log_info "Consider optimizing application or migrating to dedicated EC2"
                ;;
        esac
    elif [ "$MEM_USAGE" -lt 40 ] && [ "$DISK_USAGE" -lt 40 ]; then
        log_info "Low resource usage detected - current size is appropriate"

        case ${CURRENT_BUNDLE} in
            large_2_0)
                log_info "Could scale down to: medium_2_0 (4GB RAM) to save costs"
                ;;
            medium_2_0)
                log_info "Could scale down to: small_2_0 (2GB RAM) to save costs"
                ;;
            small_2_0)
                log_info "Current size is optimal for demo workload"
                ;;
            *)
                log_info "Instance size is appropriate"
                ;;
        esac
    else
        log_info "Resource usage is within normal range - no scaling needed"
    fi
}

verify_services_after_scaling() {
    log_info "Verifying services after scaling..."

    STATIC_IP=$(aws lightsail get-static-ip --static-ip-name ${INSTANCE_NAME}-ip --query 'staticIp.ipAddress' --output text)

    # Wait for SSH to be ready
    log_info "Waiting for SSH access..."
    for i in {1..30}; do
        if ssh -i lightsail-key.pem -o ConnectTimeout=5 ubuntu@${STATIC_IP} "echo 'SSH ready'" 2>/dev/null; then
            break
        fi
        sleep 10
    done

    # Check Docker services
    ssh -i lightsail-key.pem ubuntu@${STATIC_IP} << 'ENDSSH'
        cd /home/ubuntu/presgen
        docker-compose ps

        # Restart services if needed
        if ! docker ps | grep -q presgen-core; then
            echo "Restarting services..."
            docker-compose down
            docker-compose up -d
            sleep 60
        fi
ENDSSH

    # Health checks
    log_info "Running health checks..."
    sleep 30

    CORE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://${STATIC_IP}/health 2>/dev/null || echo "000")
    if [ "$CORE_STATUS" = "200" ]; then
        log_info "✓ Health check passed"
    else
        log_error "✗ Health check failed (HTTP $CORE_STATUS)"
        log_error "Check logs: ssh -i lightsail-key.pem ubuntu@${STATIC_IP} 'docker-compose logs'"
    fi
}

optimize_resources() {
    log_info "Optimizing resource usage..."

    STATIC_IP=$(aws lightsail get-static-ip --static-ip-name ${INSTANCE_NAME}-ip --query 'staticIp.ipAddress' --output text)

    ssh -i lightsail-key.pem ubuntu@${STATIC_IP} << 'ENDSSH'
        # Clean up Docker resources
        docker system prune -f
        docker volume prune -f

        # Clear logs older than 7 days
        find /home/ubuntu/presgen/logs -name "*.log" -mtime +7 -delete

        # Clear old temp files
        find /tmp -type f -mtime +1 -delete

        # Restart services to free memory
        cd /home/ubuntu/presgen
        docker-compose restart

        echo "Resource optimization completed"
ENDSSH

    log_info "Optimization completed"
}

add_service_replica() {
    local service_name=$1
    local replica_count=${2:-2}

    log_warn "Horizontal scaling (service replicas) is not yet implemented for Lightsail"
    log_info "Consider migrating to ECS/EKS for horizontal scaling"
    log_info ""
    log_info "Alternative: Deploy multiple Lightsail instances with load balancer"
}

estimate_costs() {
    local bundle=$1

    echo "Estimated Monthly Costs for ${bundle}:"
    case ${bundle} in
        micro_2_0)
            echo "  Instance: $5.00"
            echo "  Snapshots: $2.40 (4 weekly)"
            echo "  S3: $1.00"
            echo "  CloudWatch: $3.00"
            echo "  Total: ~$11.40/month"
            ;;
        small_2_0)
            echo "  Instance: $10.00"
            echo "  Snapshots: $2.40"
            echo "  S3: $1.00"
            echo "  CloudWatch: $3.00"
            echo "  Total: ~$16.40/month"
            ;;
        medium_2_0)
            echo "  Instance: $20.00"
            echo "  Snapshots: $2.40"
            echo "  S3: $1.00"
            echo "  CloudWatch: $3.00"
            echo "  Total: ~$26.40/month"
            ;;
        large_2_0)
            echo "  Instance: $40.00"
            echo "  Snapshots: $2.40"
            echo "  S3: $1.00"
            echo "  CloudWatch: $3.00"
            echo "  Total: ~$46.40/month"
            ;;
        *)
            echo "Unknown bundle"
            ;;
    esac
}

# ===== Main Execution =====
main() {
    log_info "PresGen Scaling Management"
    echo ""

    case ${ACTION} in
        status)
            show_scaling_status
            ;;
        up)
            TARGET_BUNDLE="${2:-small_2_0}"
            scale_up ${TARGET_BUNDLE}
            ;;
        down)
            TARGET_BUNDLE="${2:-micro_2_0}"
            scale_down ${TARGET_BUNDLE}
            ;;
        auto)
            auto_scale
            ;;
        optimize)
            optimize_resources
            ;;
        cost)
            estimate_costs "${2:-small_2_0}"
            ;;
        *)
            log_error "Unknown action: ${ACTION}"
            echo "Usage: $0 [status|up|down|auto|optimize|cost] [bundle-id]"
            echo ""
            echo "Examples:"
            echo "  $0 status                  # Show current status"
            echo "  $0 up medium_2_0          # Scale up to 4GB RAM"
            echo "  $0 down small_2_0         # Scale down to 2GB RAM"
            echo "  $0 auto                    # Auto-scale based on metrics"
            echo "  $0 optimize                # Free up resources"
            echo "  $0 cost medium_2_0        # Estimate costs for bundle"
            exit 1
            ;;
    esac
}

main
