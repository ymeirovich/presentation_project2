# Manual Testing Guide - PresGen-Assess System

_Comprehensive manual testing procedures for validating the assessment workflow system_

## Overview

This guide provides step-by-step manual testing procedures to validate all components of the PresGen-Assess system across Sprint 1-3 implementations.

## Prerequisites

Before starting manual testing, ensure:

1. **Environment Setup**:
   ```bash
   cd presgen-assess
   pip3 install -r requirements.txt
   ```

2. **Environment Variables** (`.env` file):
   ```bash
   DATABASE_URL=sqlite+aiosqlite:///./test_database.db
   OPENAI_API_KEY=your_openai_key_here
   GOOGLE_APPLICATION_CREDENTIALS=path/to/google-credentials.json
   ```

3. **Start the Server**:
   ```bash
   uvicorn src.service.http:app --reload --port 8080
   ```

4. **Verify Server Running**:
   - Open browser to `http://localhost:8080/docs`
   - Confirm FastAPI documentation loads

---

## Phase 1: Basic System Health Tests

### Test 1.1: Health Check Endpoint
**Objective**: Verify monitoring system is functional

**Steps**:
1. Open browser to `http://localhost:8080/api/v1/monitoring/health`
2. **Expected Result**: JSON response with `"overall_status": "healthy"`
3. **Verify**: All services show as "healthy" or "degraded" (not "unhealthy")

**Example Response**:
```json
{
  "overall_status": "healthy",
  "timestamp": "2025-09-27T...",
  "checks": [...],
  "summary": {
    "total_checks": 6,
    "healthy_count": 5,
    "degraded_count": 1,
    "unhealthy_count": 0
  }
}
```

### Test 1.2: System Metrics
**Objective**: Confirm system monitoring is collecting metrics

**Steps**:
1. GET `http://localhost:8080/api/v1/monitoring/metrics`
2. **Expected Result**: Detailed system metrics
3. **Verify**: CPU, memory, disk usage percentages are reasonable (<90%)

### Test 1.3: Database Connectivity
**Objective**: Ensure database operations work

**Steps**:
1. GET `http://localhost:8080/api/v1/workflows/`
2. **Expected Result**: Empty array `[]` or existing workflows
3. **Verify**: No database connection errors

---

## Phase 2: Google Forms Integration Tests

### Test 2.1: Google Forms Service Health
**Objective**: Verify Google Forms authentication and API access

**Steps**:
1. Check health endpoint for Google Forms status
2. **Expected Result**: `"google_forms"` service shows `"healthy"` or `"degraded"`
3. **If Degraded**: Check authentication setup in logs

### Test 2.2: Form Template Management
**Objective**: Test form template creation and management

**Manual Test** (via Python console):
```python
# In project directory, run python3
from src.services.form_template_manager import FormTemplateManager

template_manager = FormTemplateManager()

# Test 1: Get default template
default_template = template_manager.get_template("aws", "v1")
print(f"Template loaded: {default_template['template_id']}")

# Test 2: List available templates
templates = template_manager.list_available_templates()
print(f"Available templates: {len(templates)}")

# Expected: Should complete without errors
```

### Test 2.3: Assessment-to-Form Workflow (Mock)
**Objective**: Test the complete assessment-to-form pipeline

**Steps**:
1. POST to `http://localhost:8080/api/v1/workflows/assessment-to-form`
2. **Request Body**:
   ```json
   {
     "certification_profile_id": "123e4567-e89b-12d3-a456-426614174000",
     "user_id": "test_user@example.com",
     "assessment_data": {
       "questions": [
         {
           "id": "q1",
           "question_text": "What is AWS Lambda?",
           "question_type": "multiple_choice",
           "options": ["A) Storage", "B) Compute", "C) Database"],
           "correct_answer": "B"
         }
       ],
       "metadata": {
         "certification_name": "AWS Solutions Architect"
       }
     },
     "form_settings": {
       "collect_email": true,
       "require_login": false
     }
   }
   ```

3. **Expected Result**:
   ```json
   {
     "success": true,
     "workflow_id": "uuid-here",
     "form_id": "google-form-id",
     "form_url": "https://docs.google.com/forms/...",
     "status": "awaiting_completion"
   }
   ```

---

## Phase 3: Response Collection & Processing Tests

### Test 3.1: Response Ingestion Statistics
**Objective**: Verify response collection system is operational

**Steps**:
1. GET `http://localhost:8080/api/v1/workflows/ingestion/stats`
2. **Expected Result**: Statistics about response ingestion
3. **Verify**: No errors, reasonable statistics

### Test 3.2: Manual Response Ingestion
**Objective**: Test forced response collection for a workflow

**Prerequisites**: Complete Test 2.3 to get a workflow_id

**Steps**:
1. POST `http://localhost:8080/api/v1/workflows/{workflow_id}/force-ingest-responses`
2. **Expected Result**:
   ```json
   {
     "success": true,
     "message": "Response ingestion completed",
     "workflow_id": "uuid-here"
   }
   ```

### Test 3.3: Workflow Status Monitoring
**Objective**: Monitor workflow progress and status

**Steps**:
1. GET `http://localhost:8080/api/v1/workflows/{workflow_id}/orchestration-status`
2. **Expected Result**: Detailed workflow status
3. **Verify**: Status shows current step and progress

---

## Phase 4: PresGen Integration Tests

### Test 4.1: PresGen Integration Status
**Objective**: Check PresGen-Core connectivity and fallback capability

**Steps**:
1. GET `http://localhost:8080/api/v1/monitoring/presgen/status`
2. **Expected Results**:
   - If PresGen-Core available: `"presgen_core_available": true`
   - If not available: `"presgen_core_available": false, "fallback_mode_functional": true`

### Test 4.2: Learning Content Generation
**Objective**: Test gap-based learning content generation

**Prerequisites**: Have a workflow with gap analysis data

**Steps**:
1. POST `http://localhost:8080/api/v1/monitoring/workflows/{workflow_id}/generate-learning-content`
2. **Query Parameters**: `?content_format=slides`
3. **Expected Result**:
   ```json
   {
     "success": true,
     "learning_plan": {
       "certification_name": "...",
       "total_modules": 3,
       "learning_modules": [...],
       "study_sequence": [...]
     }
   }
   ```

### Test 4.3: PresGen Workflow Trigger
**Objective**: Test presentation generation trigger

**Steps**:
1. POST `http://localhost:8080/api/v1/monitoring/workflows/{workflow_id}/trigger-presgen`
2. **Request Body** (optional):
   ```json
   {
     "slide_count": 20,
     "avatar_enabled": true,
     "delivery_format": "presentation_with_video"
   }
   ```
3. **Expected Result**: PresGen job initiated (real or fallback mode)

---

## Phase 5: Drive Folder Organization Tests

### Test 5.1: Drive Folder Management (Code Test)
**Objective**: Test automated folder structure creation

**Manual Test** (via Python console):
```python
from src.services.drive_folder_manager import DriveFolderManager
from uuid import uuid4
import asyncio

async def test_drive_folders():
    drive_manager = DriveFolderManager()

    # Test folder structure creation
    result = await drive_manager.create_assessment_folder_structure(
        workflow_id=uuid4(),
        certification_name="AWS Test Certification",
        user_id="test@example.com"
    )

    print(f"Folder creation: {result['success']}")
    if result['success']:
        print(f"Main folder: {result['folder_structure']['main_folder_name']}")

    return result

# Run the test
result = asyncio.run(test_drive_folders())
```

**Expected**: Folder structure created successfully (or appropriate error if no Drive access)

---

## Phase 6: End-to-End Integration Tests

### Test 6.1: Complete Workflow Lifecycle
**Objective**: Test full assessment workflow from creation to completion

**Steps**:
1. **Create Workflow**: Use Test 2.3 to create assessment workflow
2. **Monitor Status**: Use Test 3.3 to check workflow progress
3. **Simulate Responses**: Use Test 3.2 to ingest mock responses
4. **Process Results**: Use Test 4.2 to generate learning content
5. **Generate Presentation**: Use Test 4.3 to trigger PresGen

**Success Criteria**: Each step completes successfully and workflow progresses through statuses

### Test 6.2: Error Handling and Recovery
**Objective**: Test system behavior under error conditions

**Steps**:
1. **Invalid Workflow ID**: Try any endpoint with non-existent workflow ID
2. **Expected**: Appropriate 404 error messages
3. **Malformed Requests**: Send invalid JSON to POST endpoints
4. **Expected**: Validation error responses
5. **Service Degradation**: Monitor health checks during high load

---

## Phase 7: Performance and Load Tests

### Test 7.1: Concurrent Workflow Creation
**Objective**: Test system under moderate concurrent load

**Manual Load Test**:
```bash
# Use curl or similar tool to create multiple workflows simultaneously
for i in {1..5}; do
  curl -X POST "http://localhost:8080/api/v1/workflows/assessment-to-form" \
    -H "Content-Type: application/json" \
    -d '{"certification_profile_id":"123e4567-e89b-12d3-a456-426614174000","user_id":"load_test_'$i'@example.com","assessment_data":{"questions":[{"id":"q1","question_text":"Test question","question_type":"multiple_choice","options":["A","B","C"],"correct_answer":"A"}],"metadata":{"certification_name":"Load Test Certification"}}}' &
done
wait
```

**Expected**: All requests complete successfully, no system errors

### Test 7.2: Memory and Resource Monitoring
**Objective**: Monitor system resources during testing

**Steps**:
1. Monitor metrics endpoint during testing: `GET /api/v1/monitoring/metrics`
2. **Watch For**:
   - Memory usage staying below 85%
   - CPU spikes returning to normal
   - No disk space issues
   - Database connection pool not exhausted

---

## Validation Checklist

### ✅ Sprint 1 Validation
- [ ] Health checks return appropriate status
- [ ] Database connectivity confirmed
- [ ] Basic API endpoints respond correctly
- [ ] Google Forms authentication working

### ✅ Sprint 2 Validation
- [ ] Assessment-to-form workflow creates successfully
- [ ] Response ingestion system functional
- [ ] Workflow orchestration tracking status
- [ ] Template management working
- [ ] Drive folder organization operational

### ✅ Sprint 3 Validation
- [ ] PresGen integration status reporting correctly
- [ ] Learning content generation from gaps working
- [ ] Presentation generation triggering (real or fallback)
- [ ] Monitoring and alerting functional
- [ ] Production readiness metrics available

### ✅ Integration Validation
- [ ] End-to-end workflow completion
- [ ] Error handling graceful
- [ ] Performance under load acceptable
- [ ] Resource usage within limits

---

## Troubleshooting Common Issues

### Issue: Health Check Shows "Unhealthy" Services
**Solution**:
1. Check logs in `src/logs/` directory
2. Verify environment variables in `.env`
3. Confirm database file exists and is writable
4. Check Google credentials if Forms service failing

### Issue: Workflow Creation Fails
**Solution**:
1. Verify request body matches schema exactly
2. Check UUIDs are valid format
3. Ensure assessment_data has required fields
4. Review API logs for specific error details

### Issue: PresGen Integration Not Working
**Solution**:
1. Expected behavior - system should fall back to local generation
2. Check `presgen_core_available: false` in status endpoint
3. Verify fallback mode generates content successfully

### Issue: Performance Degradation
**Solution**:
1. Monitor `/api/v1/monitoring/metrics` for resource usage
2. Check for database connection leaks
3. Verify no infinite loops in response ingestion
4. Review log file sizes and rotation

---

## Success Criteria Summary

**System is production-ready when**:
- All health checks pass or show expected degradations
- Complete workflows can be created and processed
- Error handling is graceful and informative
- Performance is acceptable under expected load
- Monitoring provides actionable insights
- Recovery mechanisms work as designed

**Test completion indicates**:
- All Sprint 1-3 functionality is operational
- Integration between components is working
- Production monitoring is effective
- System can handle real-world usage patterns