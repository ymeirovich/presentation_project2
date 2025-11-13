#!/bin/bash
# PresGen SQLite Backup Script
# Purpose: Automated backup of SQLite database to local and optionally S3
# Version: 1.0
# Date: 2025-11-13

set -e  # Exit on error

# Configuration
DB_FILE="${DB_FILE:-/home/ubuntu/presgen/data/assess/presgen_assess.db}"
BACKUP_DIR="${BACKUP_DIR:-/home/ubuntu/presgen/backups/sqlite}"
S3_BUCKET="${S3_BUCKET:-presgen-prod-backups}"
S3_PREFIX="${S3_PREFIX:-sqlite}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
LOG_FILE="${LOG_FILE:-/home/ubuntu/presgen/logs/backup.log}"
ENABLE_S3="${ENABLE_S3:-false}"  # Set to 'true' to upload to S3

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create directories
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log messages
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"

    case "$level" in
        "INFO")
            echo -e "${BLUE}[$level]${NC} $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[$level]${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}[$level]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[$level]${NC} $message"
            ;;
    esac
}

# Header
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PresGen SQLite Backup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

log_message "INFO" "Starting SQLite backup process"

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    log_message "ERROR" "Database file not found: $DB_FILE"
    exit 1
fi

# Get database size
DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
log_message "INFO" "Database size: $DB_SIZE"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/presgen_assess-$TIMESTAMP.db"
COMPRESSED_FILE="$BACKUP_FILE.gz"

# Create backup using SQLite backup command (safer than cp)
log_message "INFO" "Creating backup: $BACKUP_FILE"

if command -v sqlite3 &> /dev/null; then
    # Use SQLite backup command for consistency
    sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'" 2>&1 | tee -a "$LOG_FILE"

    if [ $? -eq 0 ]; then
        log_message "SUCCESS" "Backup created successfully"
    else
        log_message "ERROR" "Backup creation failed"
        exit 1
    fi
else
    # Fallback to cp if sqlite3 not available
    log_message "WARNING" "sqlite3 command not found, using cp instead"
    cp "$DB_FILE" "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        log_message "SUCCESS" "Backup copied successfully (using cp)"
    else
        log_message "ERROR" "Backup copy failed"
        exit 1
    fi
fi

# Verify backup integrity
log_message "INFO" "Verifying backup integrity"
if command -v sqlite3 &> /dev/null; then
    INTEGRITY_CHECK=$(sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" 2>&1)

    if [ "$INTEGRITY_CHECK" = "ok" ]; then
        log_message "SUCCESS" "Backup integrity verified"
    else
        log_message "ERROR" "Backup integrity check failed: $INTEGRITY_CHECK"
        rm -f "$BACKUP_FILE"
        exit 1
    fi
else
    log_message "WARNING" "Cannot verify integrity without sqlite3 command"
fi

# Compress backup
log_message "INFO" "Compressing backup"
gzip "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
    log_message "SUCCESS" "Backup compressed: $COMPRESSED_SIZE"
else
    log_message "ERROR" "Compression failed"
    exit 1
fi

# Upload to S3 (if enabled)
if [ "$ENABLE_S3" = "true" ]; then
    if command -v aws &> /dev/null; then
        log_message "INFO" "Uploading to S3: s3://$S3_BUCKET/$S3_PREFIX/"
        aws s3 cp "$COMPRESSED_FILE" "s3://$S3_BUCKET/$S3_PREFIX/presgen_assess-$TIMESTAMP.db.gz" 2>&1 | tee -a "$LOG_FILE"

        if [ $? -eq 0 ]; then
            log_message "SUCCESS" "Backup uploaded to S3"

            # List recent S3 backups
            S3_COUNT=$(aws s3 ls "s3://$S3_BUCKET/$S3_PREFIX/" | wc -l | tr -d ' ')
            log_message "INFO" "Total backups in S3: $S3_COUNT"
        else
            log_message "WARNING" "S3 upload failed (backup still saved locally)"
        fi
    else
        log_message "WARNING" "AWS CLI not found, skipping S3 upload"
    fi
else
    log_message "INFO" "S3 upload disabled (ENABLE_S3=$ENABLE_S3)"
fi

# Cleanup old local backups
log_message "INFO" "Cleaning up backups older than $RETENTION_DAYS days"
OLD_BACKUPS=$(find "$BACKUP_DIR" -name "presgen_assess-*.db.gz" -type f -mtime +$RETENTION_DAYS 2>/dev/null)
OLD_COUNT=$(echo "$OLD_BACKUPS" | grep -c "presgen_assess" || echo "0")

if [ "$OLD_COUNT" -gt 0 ]; then
    log_message "INFO" "Deleting $OLD_COUNT old backups"
    find "$BACKUP_DIR" -name "presgen_assess-*.db.gz" -type f -mtime +$RETENTION_DAYS -delete
    log_message "SUCCESS" "Old backups cleaned up"
else
    log_message "INFO" "No old backups to clean up"
fi

# Summary
TOTAL_LOCAL_BACKUPS=$(find "$BACKUP_DIR" -name "presgen_assess-*.db.gz" -type f | wc -l | tr -d ' ')
LOCAL_BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Backup Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Database file:          $DB_FILE"
echo -e "Database size:          $DB_SIZE"
echo -e "Backup file:            $COMPRESSED_FILE"
echo -e "Backup size:            ${GREEN}$COMPRESSED_SIZE${NC}"
echo -e "Local backups:          $TOTAL_LOCAL_BACKUPS"
echo -e "Local backup dir size:  $LOCAL_BACKUP_SIZE"
echo -e "S3 upload:              $([ "$ENABLE_S3" = "true" ] && echo "${GREEN}Enabled${NC}" || echo "${YELLOW}Disabled${NC}")"
echo -e "Retention period:       $RETENTION_DAYS days"
echo ""

log_message "SUCCESS" "Backup completed successfully"
log_message "INFO" "Total local backups: $TOTAL_LOCAL_BACKUPS"
log_message "INFO" "Backup directory size: $LOCAL_BACKUP_SIZE"

# Test restore (optional - uncomment to enable)
# log_message "INFO" "Testing restore procedure"
# TEST_RESTORE_FILE="/tmp/test_restore_$TIMESTAMP.db"
# gunzip -c "$COMPRESSED_FILE" > "$TEST_RESTORE_FILE"
# sqlite3 "$TEST_RESTORE_FILE" "PRAGMA integrity_check;" &>> "$LOG_FILE"
# rm -f "$TEST_RESTORE_FILE"
# log_message "SUCCESS" "Restore test passed"

exit 0
