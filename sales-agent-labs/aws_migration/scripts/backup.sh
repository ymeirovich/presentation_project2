#!/bin/bash
# Backup Script for PresGen
# Creates complete backups of:
#   - Application database
#   - User uploads
#   - Generated outputs
#   - Docker volumes
#   - Configuration files
#
# Usage: ./backup.sh [backup-type]
#   backup-type: full | database | files | config
#
# Schedule with cron:
#   Daily database backup:  0 2 * * * /home/ubuntu/presgen/scripts/backup.sh database
#   Weekly full backup:     0 3 * * 0 /home/ubuntu/presgen/scripts/backup.sh full

set -e

# ===== Configuration =====
BACKUP_DIR="/home/ubuntu/presgen/backups"
S3_BUCKET="${S3_BUCKET:-presgen-demo-files}"
S3_BACKUP_PREFIX="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30
BACKUP_TYPE="${1:-full}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ===== Functions =====

backup_database() {
    log_info "Backing up database..."

    mkdir -p ${BACKUP_DIR}/database

    # SQLite database backup
    if [ -f "/home/ubuntu/presgen/data/assess/presgen_assess.db" ]; then
        log_info "Backing up SQLite database..."

        # Online backup using docker exec
        docker exec presgen-assess sqlite3 /app/data/presgen_assess.db .dump \
            > ${BACKUP_DIR}/database/presgen_assess_${TIMESTAMP}.sql

        # Compress
        gzip ${BACKUP_DIR}/database/presgen_assess_${TIMESTAMP}.sql

        # Upload to S3
        aws s3 cp ${BACKUP_DIR}/database/presgen_assess_${TIMESTAMP}.sql.gz \
            s3://${S3_BUCKET}/${S3_BACKUP_PREFIX}/database/

        log_info "Database backup completed: presgen_assess_${TIMESTAMP}.sql.gz"
    fi

    # PostgreSQL database backup (if used)
    if docker ps | grep -q presgen-postgres; then
        log_info "Backing up PostgreSQL database..."

        docker exec presgen-postgres pg_dump -U presgen presgen_assess \
            > ${BACKUP_DIR}/database/postgres_${TIMESTAMP}.sql

        gzip ${BACKUP_DIR}/database/postgres_${TIMESTAMP}.sql

        aws s3 cp ${BACKUP_DIR}/database/postgres_${TIMESTAMP}.sql.gz \
            s3://${S3_BUCKET}/${S3_BACKUP_PREFIX}/database/

        log_info "PostgreSQL backup completed: postgres_${TIMESTAMP}.sql.gz"
    fi

    # Redis backup (if needed)
    if docker ps | grep -q presgen-redis; then
        log_info "Backing up Redis data..."

        docker exec presgen-redis redis-cli BGSAVE
        sleep 5  # Wait for background save

        docker cp presgen-redis:/data/dump.rdb ${BACKUP_DIR}/database/redis_${TIMESTAMP}.rdb
        gzip ${BACKUP_DIR}/database/redis_${TIMESTAMP}.rdb

        aws s3 cp ${BACKUP_DIR}/database/redis_${TIMESTAMP}.rdb.gz \
            s3://${S3_BUCKET}/${S3_BACKUP_PREFIX}/database/

        log_info "Redis backup completed"
    fi
}

backup_files() {
    log_info "Backing up user files..."

    mkdir -p ${BACKUP_DIR}/files

    # Backup uploads
    if [ -d "/home/ubuntu/presgen/uploads" ]; then
        log_info "Backing up uploads..."
        tar czf ${BACKUP_DIR}/files/uploads_${TIMESTAMP}.tar.gz \
            -C /home/ubuntu/presgen uploads/

        aws s3 cp ${BACKUP_DIR}/files/uploads_${TIMESTAMP}.tar.gz \
            s3://${S3_BUCKET}/${S3_BACKUP_PREFIX}/files/

        log_info "Uploads backup completed"
    fi

    # Backup outputs
    if [ -d "/home/ubuntu/presgen/output" ]; then
        log_info "Backing up generated outputs..."
        tar czf ${BACKUP_DIR}/files/output_${TIMESTAMP}.tar.gz \
            -C /home/ubuntu/presgen output/

        aws s3 cp ${BACKUP_DIR}/files/output_${TIMESTAMP}.tar.gz \
            s3://${S3_BUCKET}/${S3_BACKUP_PREFIX}/files/

        log_info "Outputs backup completed"
    fi

    # Backup exports
    if [ -d "/home/ubuntu/presgen/exports" ]; then
        log_info "Backing up exports..."
        tar czf ${BACKUP_DIR}/files/exports_${TIMESTAMP}.tar.gz \
            -C /home/ubuntu/presgen exports/

        aws s3 cp ${BACKUP_DIR}/files/exports_${TIMESTAMP}.tar.gz \
            s3://${S3_BUCKET}/${S3_BACKUP_PREFIX}/files/

        log_info "Exports backup completed"
    fi
}

backup_config() {
    log_info "Backing up configuration..."

    mkdir -p ${BACKUP_DIR}/config

    # Backup config files
    tar czf ${BACKUP_DIR}/config/config_${TIMESTAMP}.tar.gz \
        -C /home/ubuntu/presgen \
        .env \
        docker-compose.yml \
        nginx/nginx.conf \
        config.yaml \
        2>/dev/null || true

    # Backup nginx auth (exclude passwords for security)
    # Only backup user list, not password hashes
    if [ -f "/etc/nginx/auth/.htpasswd" ]; then
        cut -d: -f1 /etc/nginx/auth/.htpasswd > ${BACKUP_DIR}/config/users_${TIMESTAMP}.txt
    fi

    aws s3 cp ${BACKUP_DIR}/config/config_${TIMESTAMP}.tar.gz \
        s3://${S3_BUCKET}/${S3_BACKUP_PREFIX}/config/

    log_info "Configuration backup completed"
}

backup_docker_volumes() {
    log_info "Backing up Docker volumes..."

    mkdir -p ${BACKUP_DIR}/volumes

    # Get all volumes
    VOLUMES=$(docker volume ls --format "{{.Name}}" | grep presgen || true)

    for volume in $VOLUMES; do
        log_info "Backing up volume: $volume"

        # Create temporary container to access volume
        docker run --rm \
            -v ${volume}:/volume \
            -v ${BACKUP_DIR}/volumes:/backup \
            alpine \
            tar czf /backup/${volume}_${TIMESTAMP}.tar.gz -C /volume .

        aws s3 cp ${BACKUP_DIR}/volumes/${volume}_${TIMESTAMP}.tar.gz \
            s3://${S3_BUCKET}/${S3_BACKUP_PREFIX}/volumes/
    done

    log_info "Docker volumes backup completed"
}

backup_full() {
    log_info "Performing FULL backup..."

    backup_database
    backup_files
    backup_config
    backup_docker_volumes

    # Create manifest
    cat > ${BACKUP_DIR}/manifest_${TIMESTAMP}.txt <<EOF
PresGen Full Backup Manifest
Date: $(date)
Type: FULL
Hostname: $(hostname)

Files:
EOF

    find ${BACKUP_DIR} -name "*_${TIMESTAMP}.*" -type f -exec ls -lh {} \; >> ${BACKUP_DIR}/manifest_${TIMESTAMP}.txt

    aws s3 cp ${BACKUP_DIR}/manifest_${TIMESTAMP}.txt \
        s3://${S3_BUCKET}/${S3_BACKUP_PREFIX}/

    log_info "Full backup completed"
}

cleanup_old_backups() {
    log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."

    # Local cleanup
    find ${BACKUP_DIR} -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete
    find ${BACKUP_DIR} -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete
    find ${BACKUP_DIR} -name "*.rdb.gz" -mtime +${RETENTION_DAYS} -delete

    # S3 cleanup (using lifecycle policy is better, but this is manual)
    CUTOFF_DATE=$(date -d "${RETENTION_DAYS} days ago" +%Y-%m-%d)

    aws s3 ls s3://${S3_BUCKET}/${S3_BACKUP_PREFIX}/ --recursive | \
        while read -r line; do
            FILE_DATE=$(echo $line | awk '{print $1}')
            FILE_PATH=$(echo $line | awk '{print $4}')

            if [[ "$FILE_DATE" < "$CUTOFF_DATE" ]]; then
                log_info "Deleting old backup: $FILE_PATH"
                aws s3 rm s3://${S3_BUCKET}/${FILE_PATH}
            fi
        done

    log_info "Cleanup completed"
}

create_lightsail_snapshot() {
    log_info "Creating Lightsail instance snapshot..."

    # Get instance name from metadata or config
    INSTANCE_NAME=$(curl -s http://169.254.169.254/latest/meta-data/tags/instance/Name || echo "presgen-demo")

    SNAPSHOT_NAME="${INSTANCE_NAME}-snapshot-${TIMESTAMP}"

    aws lightsail create-instance-snapshot \
        --instance-name ${INSTANCE_NAME} \
        --instance-snapshot-name ${SNAPSHOT_NAME}

    log_info "Lightsail snapshot created: ${SNAPSHOT_NAME}"

    # Cleanup old snapshots (keep last 7)
    SNAPSHOTS=$(aws lightsail get-instance-snapshots --query 'instanceSnapshots[].name' --output text)
    SNAPSHOT_COUNT=$(echo $SNAPSHOTS | wc -w)

    if [ $SNAPSHOT_COUNT -gt 7 ]; then
        log_info "Cleaning up old snapshots (keeping last 7)..."

        # Get oldest snapshots
        OLDEST_SNAPSHOTS=$(aws lightsail get-instance-snapshots \
            --query 'instanceSnapshots[?contains(name, `'${INSTANCE_NAME}'`)] | sort_by(@, &createdAt)[0:1].name' \
            --output text)

        for snapshot in $OLDEST_SNAPSHOTS; do
            log_info "Deleting old snapshot: $snapshot"
            aws lightsail delete-instance-snapshot --instance-snapshot-name $snapshot
        done
    fi
}

send_backup_notification() {
    local status=$1
    local backup_type=$2

    if [ -n "${SNS_TOPIC_ARN:-}" ]; then
        aws sns publish \
            --topic-arn ${SNS_TOPIC_ARN} \
            --subject "PresGen Backup: ${status}" \
            --message "Backup Type: ${backup_type}
Date: $(date)
Status: ${status}
Backup Location: s3://${S3_BUCKET}/${S3_BACKUP_PREFIX}/
"
    fi
}

# ===== Main Execution =====
main() {
    log_info "Starting PresGen backup: ${BACKUP_TYPE}"
    log_info "Timestamp: ${TIMESTAMP}"

    # Create backup directory
    mkdir -p ${BACKUP_DIR}

    case ${BACKUP_TYPE} in
        full)
            backup_full
            create_lightsail_snapshot
            ;;
        database)
            backup_database
            ;;
        files)
            backup_files
            ;;
        config)
            backup_config
            ;;
        snapshot)
            create_lightsail_snapshot
            ;;
        *)
            log_error "Unknown backup type: ${BACKUP_TYPE}"
            log_info "Usage: $0 [full|database|files|config|snapshot]"
            exit 1
            ;;
    esac

    cleanup_old_backups

    log_info "Backup completed successfully!"
    log_info "Backup location: s3://${S3_BUCKET}/${S3_BACKUP_PREFIX}/"

    send_backup_notification "SUCCESS" "${BACKUP_TYPE}"
}

# Trap errors
trap 'log_error "Backup failed!"; send_backup_notification "FAILED" "${BACKUP_TYPE}"; exit 1' ERR

main
