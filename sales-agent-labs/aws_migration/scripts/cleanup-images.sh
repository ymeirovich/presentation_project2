#!/bin/bash
# PresGen Image Cleanup Script
# Purpose: Remove old Vertex AI Imagen generated images after presentations are uploaded to Google Drive
# Version: 1.0
# Date: 2025-11-13

set -e  # Exit on error

# Configuration
IMAGE_DIR="${IMAGE_DIR:-/home/ubuntu/presgen/out/images}"  # Override with env var if needed
DAYS_TO_KEEP="${DAYS_TO_KEEP:-7}"  # Keep images for 7 days by default
LOG_FILE="${LOG_FILE:-/home/ubuntu/presgen/logs/cleanup.log}"
DRY_RUN="${DRY_RUN:-false}"  # Set to 'true' to preview without deleting

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create log directory if it doesn't exist
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
echo -e "${BLUE}PresGen Image Cleanup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

log_message "INFO" "Starting image cleanup process"
log_message "INFO" "Image directory: $IMAGE_DIR"
log_message "INFO" "Retention period: $DAYS_TO_KEEP days"
log_message "INFO" "Dry run mode: $DRY_RUN"

# Check if image directory exists
if [ ! -d "$IMAGE_DIR" ]; then
    log_message "WARNING" "Image directory does not exist: $IMAGE_DIR"
    log_message "INFO" "Creating directory: $IMAGE_DIR"
    mkdir -p "$IMAGE_DIR"
    exit 0
fi

# Count total images
TOTAL_IMAGES=$(find "$IMAGE_DIR" -name "imagen_*.png" -type f 2>/dev/null | wc -l | tr -d ' ')
log_message "INFO" "Total images found: $TOTAL_IMAGES"

# Find images older than retention period
OLD_IMAGES=$(find "$IMAGE_DIR" -name "imagen_*.png" -type f -mtime +$DAYS_TO_KEEP 2>/dev/null)
OLD_COUNT=$(echo "$OLD_IMAGES" | grep -c "imagen_" || echo "0")

if [ "$OLD_COUNT" -eq 0 ]; then
    log_message "INFO" "No images older than $DAYS_TO_KEEP days found"
    echo -e "${GREEN}✓ No cleanup needed${NC}"
    exit 0
fi

log_message "INFO" "Found $OLD_COUNT images older than $DAYS_TO_KEEP days"

# Calculate disk space to be freed
SPACE_TO_FREE=0
if [ "$OLD_COUNT" -gt 0 ]; then
    SPACE_TO_FREE=$(find "$IMAGE_DIR" -name "imagen_*.png" -type f -mtime +$DAYS_TO_KEEP -exec du -k {} + 2>/dev/null | awk '{sum+=$1} END {print sum}' || echo "0")
fi

log_message "INFO" "Disk space to be freed: ${SPACE_TO_FREE}KB (~$((SPACE_TO_FREE / 1024))MB)"

# Dry run mode - just list files
if [ "$DRY_RUN" = "true" ]; then
    echo -e "${YELLOW}DRY RUN MODE - No files will be deleted${NC}"
    echo ""
    echo "Files that would be deleted:"
    echo "$OLD_IMAGES"
    echo ""
    log_message "INFO" "Dry run completed. $OLD_COUNT images would be deleted."
    exit 0
fi

# Delete old images
echo -e "${YELLOW}Deleting $OLD_COUNT images...${NC}"
DELETED_COUNT=0
FAILED_COUNT=0

while IFS= read -r file; do
    if [ -n "$file" ]; then
        if rm -f "$file" 2>/dev/null; then
            DELETED_COUNT=$((DELETED_COUNT + 1))
        else
            FAILED_COUNT=$((FAILED_COUNT + 1))
            log_message "ERROR" "Failed to delete: $file"
        fi
    fi
done <<< "$OLD_IMAGES"

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Cleanup Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Total images:           $TOTAL_IMAGES"
echo -e "Images deleted:         ${GREEN}$DELETED_COUNT${NC}"
echo -e "Failed deletions:       ${RED}$FAILED_COUNT${NC}"
echo -e "Images remaining:       $((TOTAL_IMAGES - DELETED_COUNT))"
echo -e "Disk space freed:       ${GREEN}${SPACE_TO_FREE}KB (~$((SPACE_TO_FREE / 1024))MB)${NC}"
echo ""

# Log summary
log_message "SUCCESS" "Cleanup completed: $DELETED_COUNT images deleted, $FAILED_COUNT failed"
log_message "INFO" "Disk space freed: ${SPACE_TO_FREE}KB"
log_message "INFO" "Images remaining: $((TOTAL_IMAGES - DELETED_COUNT))"

# Check if cleanup was successful
if [ "$FAILED_COUNT" -gt 0 ]; then
    log_message "WARNING" "Some deletions failed. Check permissions."
    exit 1
fi

log_message "SUCCESS" "Image cleanup completed successfully"
exit 0
