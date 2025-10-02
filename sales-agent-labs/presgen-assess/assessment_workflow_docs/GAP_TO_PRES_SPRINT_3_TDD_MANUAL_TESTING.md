# Sprint 3: PresGen-Core Integration - TDD Manual Testing Guide

## 📋 Overview

**Sprint**: Sprint 3 - PresGen-Core Integration
**Duration**: 2 weeks
**Testing Approach**: Manual TDD with mock implementations
**Test Environment**: Development (mock mode enabled)

### Sprint 3 Goals
- ✅ Database foundation with `generated_presentations` table
- ✅ Service layer (content orchestration, PresGen-Core client, background jobs)
- ✅ API endpoints for per-skill presentation generation
- 🧪 Manual testing and validation
- 📝 Documentation and deployment

### Key Architecture: Per-Skill Presentations
**Important**: Each skill gap gets its own individual presentation (3-7 minutes, 7-11 slides), NOT one comprehensive 60-minute presentation covering all skills.

---

## 🎯 Testing Objectives

### Primary Goals
1. **Validate Per-Skill Architecture**: Verify one presentation per skill generation
2. **Test Content Orchestration**: Ensure proper data preparation for each skill
3. **Verify Background Jobs**: Test async job processing with progress tracking
4. **Check Drive Organization**: Validate human-readable folder structure
5. **Test API Contracts**: Ensure frontend-backend schema compatibility
6. **Monitor Performance**: Track generation times and resource usage

### Success Criteria
- ✅ Single skill presentation generation completes successfully
- ✅ Batch generation creates multiple parallel jobs
- ✅ Progress tracking updates in real-time (0-100%)
- ✅ Drive folder paths use assessment_title + user_email + workflow_id
- ✅ Database records persist correctly with proper status transitions
- ✅ Mock mode simulates realistic behavior for testing

---

## 🔧 Pre-Testing Setup

### 1. Database Migration

```bash
# Run Sprint 3 migration
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
alembic upgrade head

# Verify table creation
sqlite3 test_database.db ".schema generated_presentations"
```

**Expected Output** (full schema with all columns):
```sql
CREATE TABLE generated_presentations (
	id VARCHAR(36) NOT NULL,
	workflow_id VARCHAR(36) NOT NULL,
	skill_id VARCHAR(255) NOT NULL,
	skill_name VARCHAR(500) NOT NULL,
	course_id VARCHAR(36),
	assessment_title VARCHAR(500),
	user_email VARCHAR(255),
	drive_folder_path TEXT,
	presentation_title VARCHAR(500) NOT NULL,
	presentation_url TEXT,
	download_url TEXT,
	drive_file_id VARCHAR(255),
	drive_folder_id VARCHAR(255),
	generation_status VARCHAR(50) DEFAULT 'pending' NOT NULL,
	generation_started_at DATETIME,
	generation_completed_at DATETIME,
	generation_duration_ms INTEGER,
	estimated_duration_minutes INTEGER,
	job_id VARCHAR(36),
	job_progress INTEGER DEFAULT '0' NOT NULL,
	job_error_message TEXT,
	template_id VARCHAR(100) DEFAULT 'short_form_skill',
	template_name VARCHAR(255) DEFAULT 'Skill-Focused Presentation',
	total_slides INTEGER,
	content_outline_id VARCHAR(36),
	file_size_mb FLOAT,
	thumbnail_url TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(workflow_id) REFERENCES workflow_executions (id) ON DELETE CASCADE,
	FOREIGN KEY(course_id) REFERENCES recommended_courses (id) ON DELETE SET NULL,
	FOREIGN KEY(content_outline_id) REFERENCES content_outlines (id) ON DELETE SET NULL,
	CONSTRAINT check_generation_status CHECK (generation_status IN ('pending', 'generating', 'completed', 'failed', 'cancelled')),
	CONSTRAINT check_job_progress_range CHECK (job_progress >= 0 AND job_progress <= 100)
);
CREATE INDEX idx_presentations_workflow ON generated_presentations (workflow_id);
CREATE INDEX idx_presentations_skill ON generated_presentations (skill_id);
CREATE INDEX idx_presentations_course ON generated_presentations (course_id);
CREATE INDEX idx_presentations_status ON generated_presentations (generation_status);
CREATE INDEX idx_presentations_job ON generated_presentations (job_id);
CREATE INDEX idx_presentations_created ON generated_presentations (created_at);
CREATE UNIQUE INDEX idx_presentations_job_unique ON generated_presentations (job_id);
```

### 2. Verify Mock Mode

```bash
# Check that PresGenCoreClient is in mock mode
grep "use_mock = True" src/service/presgen_core_client.py
```

**Expected**: `self.use_mock = True  # Mock mode for Sprint 3 testing`

### 3. Start Development Server

```bash
# Start FastAPI server (from presgen-assess directory)
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
source venv/bin/activate
uvicorn src.service.app:app --reload --port 8000

# In a new terminal, verify health check
curl http://localhost:8000/health
```

**Expected Output**:
```json
{"status":"healthy","service":"presgen-assess"}
```

### 4. Prepare Test Workflow

You'll need an existing workflow with:
- ✅ Completed assessment (workflow.assessment_data has questions/answers)
- ✅ Gap analysis performed (gap_analysis table has entries)
- ✅ Content outlines generated (content_outlines table populated)
- ✅ Recommended courses available (recommended_courses table)

**Get Test Workflow ID**:
```bash
sqlite3 test_database.db "SELECT id, status, created_at FROM workflow_executions ORDER BY created_at DESC LIMIT 1;"
```

**Example Output**:
```
8e46398dc2924439a04531dfeb49d7ef|completed|2025-10-01 11:28:38
```

**Get Test Course ID**:
```bash
# Replace {workflow_id} with your test workflow ID
sqlite3 test_database.db "SELECT id, skill_name FROM recommended_courses WHERE workflow_id = '{workflow_id}' LIMIT 1;"
```

**Example Output**:
```
0f524bb9d7f343d6867c9597b2f91804|Security
```

---

## 🧪 Test Case 1: Single Skill Presentation Generation

### Objective
Generate a presentation for ONE skill/course and verify the complete flow from API request to database persistence.

### Prerequisites
- Workflow ID with completed gap analysis
- Course ID for a specific skill
- Development server running

### Test Steps

#### Step 1.1: Submit Generation Request

```bash
# Replace {workflow_id} and {course_id} with actual UUIDs
curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/courses/{course_id}/generate-presentation" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "{workflow_id}",
    "course_id": "{course_id}",
    "custom_title": "Mastering EC2 Instance Types"
  }'
```

**Expected Response (HTTP 202 Accepted)**:
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "presentation_id": "660e8400-e29b-41d4-a716-446655440001",
  "message": "Presentation generation started for EC2 Instance Types",
  "estimated_duration_seconds": 300,
  "status_check_url": "/api/v1/workflows/{workflow_id}/presentations/{presentation_id}/status"
}
```

**Validation Checklist**:
- ✅ HTTP status code is 202 (Accepted)
- ✅ Response contains `job_id` (UUID format)
- ✅ Response contains `presentation_id` (UUID format)
- ✅ `estimated_duration_seconds` is 300 (5 minutes)
- ✅ `status_check_url` follows correct pattern
- ✅ `message` includes skill name

#### Step 1.2: Check Initial Database State

```bash
# Query presentation record
sqlite3 test_database.db "SELECT id, skill_name, generation_status, job_id, job_progress FROM generated_presentations WHERE id = '{presentation_id}';"
```

**Expected Output**:
```
{presentation_id}|EC2 Instance Types|pending|{job_id}|0
```

**Validation Checklist**:
- ✅ Record exists in `generated_presentations` table
- ✅ `generation_status` is 'pending'
- ✅ `job_id` matches response
- ✅ `job_progress` is 0
- ✅ `skill_name` matches course skill

#### Step 1.3: Monitor Progress (Real-Time Polling)

```bash
# Poll status every 2 seconds (mock completes in ~1 second)
for i in {1..5}; do
  echo "=== Check $i ==="
  curl "http://localhost:8000/api/v1/workflows/{workflow_id}/presentations/{presentation_id}/status"
  echo ""
  sleep 2
done
```

**Expected Progress Sequence**:

**Check 1 (t=0s)**: Validating content
```json
{
  "job_id": "{job_id}",
  "presentation_id": "{presentation_id}",
  "status": "generating",
  "progress": 10,
  "current_step": "Validating content",
  "error_message": null
}
```

**Check 2 (t=2s)**: Generation complete (mock mode is fast)
```json
{
  "job_id": "{job_id}",
  "presentation_id": "{presentation_id}",
  "status": "completed",
  "progress": 100,
  "current_step": "Complete",
  "error_message": null
}
```

**Validation Checklist**:
- ✅ Status transitions: pending → generating → completed
- ✅ Progress increases: 0 → 10 → 20 → ... → 100
- ✅ `current_step` updates with meaningful descriptions
- ✅ `error_message` remains null
- ✅ Final status is 'completed'

#### Step 1.4: Verify Final Database State

```bash
# Query complete record
sqlite3 test_database.db "SELECT skill_name, generation_status, job_progress, presentation_url, drive_folder_path, drive_file_id, total_slides FROM generated_presentations WHERE id = '{presentation_id}';"
```

**Expected Output**:
```
EC2 Instance Types|completed|100|https://docs.google.com/presentation/d/mock-abc123/edit|Assessments/AWS_Solutions_Architect_user@email.com_abc123/Presentations/EC2_Instance_Types/|mock-abc123|9
```

**Validation Checklist**:
- ✅ `generation_status` = 'completed'
- ✅ `job_progress` = 100
- ✅ `presentation_url` contains Google Slides mock URL
- ✅ `drive_folder_path` uses format: `Assessments/{assessment_title}_{user_email}_{workflow_id}/Presentations/{skill_name}/`
- ✅ `drive_file_id` is populated (mock ID)
- ✅ `total_slides` is between 7-11 (short-form)
- ✅ `generation_started_at` and `generation_completed_at` are set
- ✅ `generation_duration_ms` is reasonable (mock: ~1000ms)

#### Step 1.5: Check Server Logs

**Search for key log entries**:
```bash
# In development server terminal, look for:
```

**Expected Log Sequence**:
```
📋 Generate presentation request | workflow={workflow_id} | course={course_id}
✅ Presentation generation started | job_id={job_id} | skill=EC2 Instance Types
🎬 Starting presentation generation | job_id={job_id} | skill=EC2 Instance Types
📊 Progress: 10% | Validating content
📊 Progress: 20% | Generating slide structure
📊 Progress: 40% | Creating slide content
📊 Progress: 60% | Applying template design
📊 Progress: 80% | Saving to Google Drive
📊 Progress: 90% | Finalizing metadata
✅ Presentation generation complete | job_id={job_id} | duration=1.2s
```

**Validation Checklist**:
- ✅ Logs show complete generation flow
- ✅ Progress updates appear in sequence
- ✅ No error or warning messages
- ✅ Duration is reasonable (~1 second in mock mode)

---

## 🧪 Test Case 2: Duplicate Prevention

### Objective
Verify that the system prevents generating duplicate presentations for the same skill.

### Test Steps

#### Step 2.1: Attempt Duplicate Generation

```bash
# Use same workflow_id and course_id from Test Case 1
curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/courses/{course_id}/generate-presentation" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "{workflow_id}",
    "course_id": "{course_id}"
  }'
```

**Expected Response (HTTP 202 Accepted)**:
```json
{
  "success": true,
  "job_id": "completed",
  "presentation_id": "{existing_presentation_id}",
  "message": "Presentation already exists for EC2 Instance Types",
  "estimated_duration_seconds": 0,
  "status_check_url": "/api/v1/workflows/{workflow_id}/presentations/{existing_presentation_id}/status"
}
```

**Validation Checklist**:
- ✅ Response indicates existing presentation
- ✅ `job_id` is "completed" (not a new UUID)
- ✅ `presentation_id` matches existing record
- ✅ `estimated_duration_seconds` is 0
- ✅ Message clearly states "already exists"
- ✅ No new database record created

#### Step 2.2: Verify Database Uniqueness

```bash
# Count presentations for this skill/workflow
sqlite3 test_database.db "SELECT COUNT(*) FROM generated_presentations WHERE workflow_id = '{workflow_id}' AND skill_id = '{skill_id}' AND generation_status = 'completed';"
```

**Expected Output**: `1` (only one completed presentation per skill)

**Validation Checklist**:
- ✅ Partial unique index enforces one completed presentation per skill/workflow
- ✅ No duplicate records exist
- ✅ System gracefully returns existing presentation

---

## 🧪 Test Case 3: Batch Generation (All Skills)

### Objective
Generate presentations for ALL courses in a workflow using parallel job execution.

### Test Steps

#### Step 3.1: Submit Batch Generation Request

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/generate-all-presentations" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "{workflow_id}",
    "max_concurrent": 3
  }'
```

**Expected Response (HTTP 202 Accepted)**:
```json
{
  "success": true,
  "jobs": [
    {
      "job_id": "job-uuid-1",
      "presentation_id": "pres-uuid-1",
      "skill_name": "EC2 Instance Types"
    },
    {
      "job_id": "job-uuid-2",
      "presentation_id": "pres-uuid-2",
      "skill_name": "VPC Networking"
    },
    {
      "job_id": "job-uuid-3",
      "presentation_id": "pres-uuid-3",
      "skill_name": "S3 Storage Classes"
    }
  ],
  "message": "Started generation for 3 skill presentations",
  "total_presentations": 3,
  "estimated_total_duration_seconds": 300
}
```

**Validation Checklist**:
- ✅ HTTP status code is 202 (Accepted)
- ✅ `jobs` array contains one entry per course
- ✅ Each job has unique `job_id` and `presentation_id`
- ✅ `total_presentations` matches course count
- ✅ `estimated_total_duration_seconds` calculated correctly:
  - Formula: `ceil(total_jobs / max_concurrent) * 300`
  - Example: `ceil(3 / 3) * 300 = 300` (1 batch)
  - Example: `ceil(9 / 3) * 300 = 900` (3 batches)

#### Step 3.2: Check Database for All Jobs

```bash
# List all presentations for workflow
sqlite3 test_database.db "SELECT skill_name, generation_status, job_progress FROM generated_presentations WHERE workflow_id = '{workflow_id}' ORDER BY created_at DESC;"
```

**Expected Output**:
```
S3 Storage Classes|pending|0
VPC Networking|pending|0
EC2 Instance Types|completed|100
```

**Validation Checklist**:
- ✅ New presentation records created for each course
- ✅ Existing completed presentations not duplicated
- ✅ All new records start with 'pending' status
- ✅ Initial `job_progress` is 0

#### Step 3.3: Monitor Parallel Execution

```bash
# Poll list endpoint to see progress
for i in {1..5}; do
  echo "=== Check $i ==="
  curl "http://localhost:8000/api/v1/workflows/{workflow_id}/presentations" | jq '.presentations[] | {skill_name, status: .generation_status, progress: .job_progress}'
  echo ""
  sleep 2
done
```

**Expected Progress Sequence**:

**Check 1 (t=0s)**: All jobs starting
```json
[
  {"skill_name": "S3 Storage Classes", "status": "generating", "progress": 10},
  {"skill_name": "VPC Networking", "status": "generating", "progress": 10},
  {"skill_name": "EC2 Instance Types", "status": "completed", "progress": 100}
]
```

**Check 2 (t=2s)**: Jobs completing (mock mode is fast)
```json
[
  {"skill_name": "S3 Storage Classes", "status": "completed", "progress": 100},
  {"skill_name": "VPC Networking", "status": "completed", "progress": 100},
  {"skill_name": "EC2 Instance Types", "status": "completed", "progress": 100}
]
```

**Validation Checklist**:
- ✅ Jobs execute in parallel (multiple 'generating' at once)
- ✅ All jobs complete successfully
- ✅ Final status is 'completed' for all
- ✅ Progress reaches 100% for all
- ✅ No failed jobs

---

## 🧪 Test Case 4: Drive Folder Organization

### Objective
Verify that Drive folder paths use human-readable format with assessment title, user email, and workflow ID.

### Test Steps

#### Step 4.1: Check Folder Path Format

```bash
# Query all drive folder paths
sqlite3 test_database.db "SELECT skill_name, drive_folder_path FROM generated_presentations WHERE workflow_id = '{workflow_id}';"
```

**Expected Output (with user_email)**:
```
EC2 Instance Types|Assessments/AWS_Solutions_Architect_user@email.com_abc123/Presentations/EC2_Instance_Types/
VPC Networking|Assessments/AWS_Solutions_Architect_user@email.com_abc123/Presentations/VPC_Networking/
S3 Storage Classes|Assessments/AWS_Solutions_Architect_user@email.com_abc123/Presentations/S3_Storage_Classes/
```

**Expected Output (without user_email)**:
```
EC2 Instance Types|Assessments/AWS_Solutions_Architect_abc123/Presentations/EC2_Instance_Types/
VPC Networking|Assessments/AWS_Solutions_Architect_abc123/Presentations/VPC_Networking/
S3 Storage Classes|Assessments/AWS_Solutions_Architect_abc123/Presentations/S3_Storage_Classes/
```

**Validation Checklist**:
- ✅ Base folder uses format: `Assessments/{assessment_title}_{user_email}_{workflow_id}/`
- ✅ User email included if available, omitted if null
- ✅ Workflow ID truncated to first 8 characters
- ✅ Skill folder uses format: `Presentations/{skill_name}/`
- ✅ Special characters replaced with underscores
- ✅ Spaces replaced with underscores
- ✅ All paths are consistent across skills

#### Step 4.2: Verify Metadata Fields

```bash
# Check assessment_title and user_email storage
sqlite3 test_database.db "SELECT DISTINCT assessment_title, user_email FROM generated_presentations WHERE workflow_id = '{workflow_id}';"
```

**Expected Output**:
```
AWS Solutions Architect|user@email.com
```

**Validation Checklist**:
- ✅ `assessment_title` stored correctly (original form, not sanitized)
- ✅ `user_email` stored correctly (or NULL if not available)
- ✅ Values consistent across all presentations in workflow

---

## 🧪 Test Case 5: Content Orchestration

### Objective
Verify that ContentOrchestrationService correctly prepares content specifications for single-skill presentations.

### Test Steps

#### Step 5.1: Enable Debug Logging

```python
# Add to src/service/content_orchestration.py temporarily
logger.setLevel(logging.DEBUG)
```

#### Step 5.2: Generate Presentation with Logging

```bash
# Repeat Test Case 1 with debug logging enabled
curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/courses/{course_id}/generate-presentation" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "{workflow_id}",
    "course_id": "{course_id}"
  }'
```

#### Step 5.3: Review Server Logs

**Expected Log Entries**:
```
DEBUG: Preparing content spec | workflow={workflow_id} | course={course_id}
DEBUG: Fetched course | skill_id={skill_id} | skill_name=EC2 Instance Types
DEBUG: Fetched gap analysis | skill_gaps_count=3
DEBUG: Extracted skill gap | skill_id={skill_id} | score=65.0
DEBUG: Fetched content outline | items_count=5
DEBUG: Fetched workflow metadata | assessment_title=AWS Solutions Architect
DEBUG: Built content spec | template_type=single_skill | overall_score=72.5
```

**Validation Checklist**:
- ✅ Course fetched successfully
- ✅ Gap analysis filtered to specific skill
- ✅ Content outline matched to skill
- ✅ Workflow metadata extracted (assessment_title, user_email)
- ✅ Content spec built with single skill data
- ✅ Template type is 'single_skill' (not 'comprehensive')

---

## 🧪 Test Case 6: Error Handling

### Objective
Test error scenarios and validate proper error responses.

### Test Steps

#### Step 6.1: Invalid Workflow ID

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/invalid-uuid/courses/{course_id}/generate-presentation" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "invalid-uuid",
    "course_id": "{course_id}"
  }'
```

**Expected Response (HTTP 422 Unprocessable Entity)**:
```json
{
  "detail": [
    {
      "loc": ["path", "workflow_id"],
      "msg": "value is not a valid uuid",
      "type": "type_error.uuid"
    }
  ]
}
```

#### Step 6.2: Non-Existent Course

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/courses/00000000-0000-0000-0000-000000000000/generate-presentation" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "{workflow_id}",
    "course_id": "00000000-0000-0000-0000-000000000000"
  }'
```

**Expected Response (HTTP 404 Not Found)**:
```json
{
  "detail": "Course 00000000-0000-0000-0000-000000000000 not found"
}
```

#### Step 6.3: Mismatched Request Body

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/courses/{course_id}/generate-presentation" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "different-uuid",
    "course_id": "{course_id}"
  }'
```

**Expected Response (HTTP 400 Bad Request)**:
```json
{
  "detail": "Workflow ID or Course ID in request doesn't match URL parameters"
}
```

**Validation Checklist**:
- ✅ Invalid UUID format returns HTTP 422
- ✅ Non-existent resources return HTTP 404
- ✅ Request body validation returns HTTP 400
- ✅ Error messages are clear and actionable
- ✅ No server crashes or 500 errors

---

## 🧪 Test Case 7: List Presentations Endpoint

### Objective
Verify the list endpoint returns all presentations with correct counts and statistics.

### Test Steps

#### Step 7.1: Query List Endpoint

```bash
curl "http://localhost:8000/api/v1/workflows/{workflow_id}/presentations"
```

**Expected Response (HTTP 200 OK)**:
```json
{
  "workflow_id": "{workflow_id}",
  "presentations": [
    {
      "id": "{presentation_id_1}",
      "workflow_id": "{workflow_id}",
      "skill_id": "ec2-instance-types",
      "skill_name": "EC2 Instance Types",
      "course_id": "{course_id_1}",
      "assessment_title": "AWS Solutions Architect",
      "user_email": "user@email.com",
      "drive_folder_path": "Assessments/AWS_Solutions_Architect_user@email.com_abc123/Presentations/EC2_Instance_Types/",
      "presentation_title": "Mastering EC2 Instance Types",
      "presentation_url": "https://docs.google.com/presentation/d/mock-abc123/edit",
      "download_url": "https://docs.google.com/presentation/d/mock-abc123/export/pptx",
      "drive_file_id": "mock-abc123",
      "generation_status": "completed",
      "generation_started_at": "2025-10-02T10:00:00",
      "generation_completed_at": "2025-10-02T10:00:05",
      "generation_duration_ms": 1200,
      "estimated_duration_minutes": 5.0,
      "job_id": "job-uuid-1",
      "job_progress": 100,
      "job_error_message": null,
      "template_name": "Skill-Focused Presentation",
      "total_slides": 9,
      "file_size_mb": 2.5,
      "thumbnail_url": "https://docs.google.com/presentation/d/mock-abc123/thumbnail",
      "created_at": "2025-10-02T10:00:00",
      "updated_at": "2025-10-02T10:00:05"
    }
    // ... more presentations
  ],
  "total_count": 3,
  "completed_count": 3,
  "pending_count": 0,
  "generating_count": 0,
  "failed_count": 0
}
```

**Validation Checklist**:
- ✅ All presentations for workflow returned
- ✅ Presentations ordered by `created_at DESC` (newest first)
- ✅ Count summaries accurate:
  - `total_count` = length of `presentations` array
  - `completed_count` = presentations with status='completed'
  - `pending_count` = presentations with status='pending'
  - `generating_count` = presentations with status='generating'
  - `failed_count` = presentations with status='failed'
- ✅ All fields populated correctly
- ✅ UUIDs properly formatted
- ✅ Timestamps in ISO 8601 format
- ✅ URLs valid format (even if mock)

---

## 📊 Performance Testing

### Test Case 8: Generation Time Tracking

#### Objective
Verify generation duration tracking and performance metrics.

#### Test Steps

**Step 8.1**: Generate presentation and capture timestamps

```bash
# Start time
START_TIME=$(date +%s)

# Submit request
RESPONSE=$(curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/courses/{course_id}/generate-presentation" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "{workflow_id}",
    "course_id": "{course_id}"
  }')

PRESENTATION_ID=$(echo $RESPONSE | jq -r '.presentation_id')

# Poll until complete
while true; do
  STATUS=$(curl -s "http://localhost:8000/api/v1/workflows/{workflow_id}/presentations/${PRESENTATION_ID}/status" | jq -r '.status')
  if [ "$STATUS" == "completed" ]; then
    break
  fi
  sleep 1
done

# End time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo "Generation completed in ${ELAPSED} seconds"
```

**Step 8.2**: Query database for duration

```bash
sqlite3 test_database.db "SELECT generation_duration_ms FROM generated_presentations WHERE id = '${PRESENTATION_ID}';"
```

**Validation Checklist**:
- ✅ Mock mode completes in ~1-2 seconds (fast for testing)
- ✅ Database `generation_duration_ms` matches actual elapsed time
- ✅ `generation_started_at` and `generation_completed_at` accurate
- ✅ Duration calculation: `generation_duration_ms = (completed_at - started_at) * 1000`

**Production Expectations**:
- 🎯 Real generation: 3-7 minutes per presentation
- 🎯 Batch generation: ~5 minutes per batch (parallel execution)
- 🎯 Content orchestration: < 5 seconds
- 🎯 Database operations: < 100ms

---

## 🔍 Integration Testing

### Test Case 9: End-to-End Workflow

#### Objective
Test complete workflow from assessment creation through presentation generation.

#### Prerequisites
- Fresh database or clean workflow state

#### Test Steps

**Step 9.1**: Create Assessment
```bash
# Create assessment (use existing assessment creation endpoint)
# ... (details omitted for brevity)
```

**Step 9.2**: Execute Workflow
```bash
# Execute assessment workflow
# ... (details omitted)
```

**Step 9.3**: Perform Gap Analysis
```bash
# Run gap analysis
# ... (details omitted)
```

**Step 9.4**: Generate Presentations
```bash
# Use batch generation for all skills
curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/generate-all-presentations" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "{workflow_id}",
    "max_concurrent": 3
  }'
```

**Step 9.5**: Verify Complete State
```bash
# Check all presentations completed
curl "http://localhost:8000/api/v1/workflows/{workflow_id}/presentations" | jq '.completed_count == .total_count'
```

**Expected Output**: `true`

**Validation Checklist**:
- ✅ Complete workflow executes without errors
- ✅ All presentations generated successfully
- ✅ Database consistency maintained throughout
- ✅ Foreign key relationships preserved
- ✅ No orphaned records

---

## 🐛 Edge Cases & Failure Scenarios

### Test Case 10: Job Failure Handling

#### Objective
Test system behavior when generation fails.

**Note**: In mock mode, failures must be simulated by temporarily modifying code. For real testing, this would occur naturally from API errors.

#### Simulation Steps

**Step 10.1**: Temporarily modify `presgen_core_client.py`

```python
# In generate_presentation() method, add:
if content_spec.skill_name == "Test Failure Skill":
    raise Exception("Simulated generation failure")
```

**Step 10.2**: Create course with skill name "Test Failure Skill"

**Step 10.3**: Generate presentation

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/courses/{course_id}/generate-presentation" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "{workflow_id}",
    "course_id": "{course_id}"
  }'
```

**Step 10.4**: Check status

```bash
curl "http://localhost:8000/api/v1/workflows/{workflow_id}/presentations/{presentation_id}/status"
```

**Expected Response**:
```json
{
  "job_id": "{job_id}",
  "presentation_id": "{presentation_id}",
  "status": "failed",
  "progress": 20,
  "current_step": null,
  "error_message": "Simulated generation failure"
}
```

**Step 10.5**: Verify database

```bash
sqlite3 test_database.db "SELECT generation_status, job_error_message FROM generated_presentations WHERE id = '{presentation_id}';"
```

**Expected Output**:
```
failed|Simulated generation failure
```

**Validation Checklist**:
- ✅ Status transitions to 'failed'
- ✅ Error message captured in `job_error_message`
- ✅ Progress frozen at failure point
- ✅ No partial/corrupt data in database
- ✅ Other jobs continue unaffected (if batch)

---

## ✅ Test Results Summary

### Results Template

After completing all test cases, fill out this summary:

```markdown
## Sprint 3 Test Results

**Test Date**: YYYY-MM-DD
**Tester**: [Your Name]
**Environment**: Development (Mock Mode)

### Test Case Results

| Test Case | Status | Duration | Notes |
|-----------|--------|----------|-------|
| TC1: Single Skill Generation | ✅ PASS | 2s | Mock completed successfully |
| TC2: Duplicate Prevention | ✅ PASS | <1s | Returned existing presentation |
| TC3: Batch Generation | ✅ PASS | 3s | 3 jobs executed in parallel |
| TC4: Drive Folder Organization | ✅ PASS | N/A | Paths formatted correctly |
| TC5: Content Orchestration | ✅ PASS | <1s | Debug logs verified |
| TC6: Error Handling | ✅ PASS | <1s | All error scenarios handled |
| TC7: List Presentations | ✅ PASS | <1s | Counts accurate |
| TC8: Performance Tracking | ✅ PASS | 2s | Duration tracked correctly |
| TC9: End-to-End Workflow | ✅ PASS | 5s | Complete flow successful |
| TC10: Job Failure Handling | ✅ PASS | 1s | Failure captured properly |

### Summary Statistics

- **Total Test Cases**: 10
- **Passed**: 10
- **Failed**: 0
- **Blocked**: 0
- **Pass Rate**: 100%

### Critical Issues Found

None

### Recommendations

1. Ready for production PresGen-Core integration (disable mock mode)
2. Implement Redis-backed job queue for scalability
3. Add monitoring dashboards for job progress
4. Set up alerts for failed presentations
5. Consider retry logic for transient failures

### Sign-Off

- ✅ Database schema correct
- ✅ Service layer functional
- ✅ API endpoints operational
- ✅ Per-skill architecture validated
- ✅ Drive organization verified
- ✅ Error handling robust
- ✅ Documentation complete

**Status**: READY FOR SPRINT 4
```

---

## 📚 Additional Resources

### Database Schema Reference

```sql
-- Quick reference for Sprint 3 schema
SELECT
  id,
  skill_name,
  generation_status,
  job_progress,
  presentation_url,
  drive_folder_path
FROM generated_presentations
WHERE workflow_id = '{workflow_id}'
ORDER BY created_at DESC;
```

### Useful SQL Queries

**Count presentations by status**:
```sql
SELECT generation_status, COUNT(*) as count
FROM generated_presentations
WHERE workflow_id = '{workflow_id}'
GROUP BY generation_status;
```

**Find failed presentations**:
```sql
SELECT skill_name, job_error_message, created_at
FROM generated_presentations
WHERE generation_status = 'failed'
ORDER BY created_at DESC;
```

**Average generation time**:
```sql
SELECT AVG(generation_duration_ms) / 1000.0 as avg_seconds
FROM generated_presentations
WHERE generation_status = 'completed';
```

**Drive folder summary**:
```sql
SELECT DISTINCT drive_folder_path
FROM generated_presentations
WHERE workflow_id = '{workflow_id}'
AND drive_folder_path IS NOT NULL;
```

### API Quick Reference

```bash
# Base URL
BASE_URL="http://localhost:8000/api/v1"

# Single generation
POST ${BASE_URL}/workflows/{workflow_id}/courses/{course_id}/generate-presentation

# Batch generation
POST ${BASE_URL}/workflows/{workflow_id}/generate-all-presentations

# Check status
GET ${BASE_URL}/workflows/{workflow_id}/presentations/{presentation_id}/status

# List all
GET ${BASE_URL}/workflows/{workflow_id}/presentations
```

---

## 🎯 Next Steps After Testing

### 1. Switch to Production Mode

**File**: `src/service/presgen_core_client.py`

```python
# Change from:
self.use_mock = True

# To:
self.use_mock = False  # Use real PresGen-Core API
```

### 2. Configure Real API Endpoint

```python
# Set environment variable
PRESGEN_CORE_API_URL=https://presgen-core.production.com
```

### 3. Test with Real PresGen-Core

- Repeat Test Cases 1-3 with production PresGen-Core
- Verify actual Google Drive integration
- Validate real slide generation quality
- Measure actual generation times (3-7 minutes)

### 4. Production Readiness Checklist

- [ ] Alembic migration applied to production database
- [ ] Environment variables configured
- [ ] Google Drive credentials validated
- [ ] PresGen-Core API accessible
- [ ] Monitoring dashboards set up
- [ ] Error alerting configured
- [ ] Load testing completed
- [ ] Documentation updated
- [ ] User acceptance testing passed
- [ ] Deployment runbook prepared

---

## 📞 Support & Troubleshooting

### Common Issues

**Issue**: "Table generated_presentations does not exist"
- **Solution**: Run `alembic upgrade head`

**Issue**: "Course not found"
- **Solution**: Ensure gap analysis and courses generated for workflow

**Issue**: "Jobs stuck in 'generating' status"
- **Solution**: Check background job queue, restart server if needed

**Issue**: "Drive folder path incorrect format"
- **Solution**: Verify assessment_title and user_email in workflow metadata

### Debug Commands

```bash
# Check table exists
sqlite3 test_database.db ".tables" | grep generated_presentations

# View recent logs
tail -f logs/presgen_assess.log | grep -E "presentation|job"

# Kill stuck background jobs (restart server)
pkill -f "uvicorn src.service.main:app"

# Check Alembic version
alembic current
```

---

**Document Version**: 1.0
**Created**: 2025-10-02
**Sprint**: Sprint 3 - PresGen-Core Integration
**Status**: ✅ Ready for Testing
