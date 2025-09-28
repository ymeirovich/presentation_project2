# Sprint 1 TDD Manual Testing Instructions

## Overview
This document provides comprehensive manual testing instructions for Sprint 1 stability fixes and enhancements. All tests must be performed and pass before Sprint 1 is considered complete.

## Pre-Testing Setup

### Environment Requirements
```bash
# Ensure PresGen-Assess server is running
cd presgen-assess
uvicorn src.service.http:app --reload --port 8081

# Ensure PresGen-UI is running
cd presgen-ui
npm run dev
```

### Test Data Setup
- Create test certification profile: "AWS Machine Learning - Test"
- Upload test resources: exam guide PDF, transcript file
- Prepare test user account: `test_user@example.com`

---

## Test 1: Workflow Continuation Validation

### Test ID: SPRINT1-001
### Priority: CRITICAL
### Estimated Time: 15 minutes

#### Scenario
Verify that workflow orchestrator continues existing workflows instead of creating duplicates.

#### Steps
1. **Start Assessment Workflow**
   ```
   POST /api/v1/google-forms/create
   {
     "certificationId": "test-cert-id",
     "title": "Test Assessment - Continuation Check",
     "summaryMarkdown": "Testing workflow continuation functionality"
   }
   ```

2. **Record Initial Workflow ID**
   - Note the `workflow_id` from response
   - Navigate to Workflow Timeline in UI
   - Verify workflow shows as "initiated" status

3. **Simulate Server Restart**
   - Stop the PresGen-Assess server (Ctrl+C)
   - Wait 5 seconds
   - Restart server: `uvicorn src.service.http:app --reload --port 8081`

4. **Trigger Same Assessment Again**
   - Submit identical assessment request
   - **Expected**: Same workflow ID returned
   - **Expected**: No duplicate workflows created

5. **Verify Database State**
   ```sql
   SELECT id, user_id, execution_status, current_step, created_at
   FROM workflow_execution
   WHERE user_id = 'test_user@example.com'
   ORDER BY created_at DESC;
   ```

#### Expected Results
- ✅ Same workflow ID returned on retry
- ✅ Only one workflow record in database
- ✅ Workflow continues from existing stage
- ✅ No duplicate Google Forms created
- ✅ Correlation IDs remain consistent in logs

#### Failure Conditions
- ❌ New workflow ID generated
- ❌ Multiple workflow records for same user/certification
- ❌ Duplicate Google Forms created

---

## Test 2: DateTime Serialization Edge Cases

### Test ID: SPRINT1-002
### Priority: CRITICAL
### Estimated Time: 20 minutes

#### Scenario
Verify response ingestion handles various datetime formats without serialization errors.

#### Steps
1. **Create Test Workflow**
   - Generate assessment and Google Form
   - Progress to "collect_responses" stage

2. **Test Different Timestamp Formats**

   **Test Case 2.1: ISO 8601 with Z**
   ```json
   {
     "lastSubmittedTime": "2025-09-28T15:30:00Z",
     "respondentEmail": "test1@example.com"
   }
   ```

   **Test Case 2.2: ISO 8601 with Timezone**
   ```json
   {
     "lastSubmittedTime": "2025-09-28T15:30:00+00:00",
     "respondentEmail": "test2@example.com"
   }
   ```

   **Test Case 2.3: Local Timezone**
   ```json
   {
     "lastSubmittedTime": "2025-09-28T11:30:00-04:00",
     "respondentEmail": "test3@example.com"
   }
   ```

3. **Force Response Ingestion**
   ```
   POST /api/v1/workflows/{workflow_id}/force-ingest-responses
   ```

4. **Verify Response Storage**
   - Check workflow.collected_responses in database
   - Verify all timestamps stored as ISO strings
   - Confirm no datetime objects in JSON fields

#### Expected Results
- ✅ All datetime formats processed successfully
- ✅ Timestamps stored as ISO strings in JSON
- ✅ No serialization errors in logs
- ✅ Response data maintains integrity
- ✅ Manual ingestion completes without errors

#### Failure Conditions
- ❌ Datetime serialization errors in logs
- ❌ Raw datetime objects stored in JSON fields
- ❌ Response ingestion fails
- ❌ Data corruption or loss

---

## Test 3: Gap Analysis Dashboard Error Recovery

### Test ID: SPRINT1-003
### Priority: HIGH
### Estimated Time: 10 minutes

#### Scenario
Verify Gap Analysis Dashboard handles API failures gracefully and provides navigation options.

#### Steps
1. **Create Completed Workflow**
   - Generate assessment workflow
   - Manually progress to "completed" status (progress ≥ 75%)

2. **Test Normal Gap Analysis Access**
   - Navigate to Workflow Timeline
   - Click on completed workflow
   - Verify Gap Analysis Dashboard loads correctly

3. **Simulate API Failure**
   - Temporarily modify endpoint to return 500 error
   - Or block network request in browser dev tools
   - Refresh Gap Analysis Dashboard

4. **Verify Error State UI**
   - Confirm error message displays clearly
   - **CRITICAL**: Verify Back button appears in error state
   - Test "Try Again" button functionality

5. **Test Navigation Recovery**
   - Click Back button → Should return to Workflow Timeline
   - Navigate back to Gap Analysis
   - Restore API functionality
   - Click "Try Again" → Should load successfully

#### Expected Results
- ✅ Back button visible in all states (loading, error, success)
- ✅ Clear error messaging for API failures
- ✅ "Try Again" button functions correctly
- ✅ Navigation works from error state
- ✅ Recovery possible after API restoration

#### Failure Conditions
- ❌ Back button missing in error/loading states
- ❌ User trapped in error state without navigation
- ❌ Unclear or missing error messages

---

## Test 4: Enhanced Logging Verification

### Test ID: SPRINT1-004
### Priority: MEDIUM
### Estimated Time: 15 minutes

#### Scenario
Verify structured logging captures workflow stages with correlation IDs.

#### Steps
1. **Start Fresh Assessment**
   - Create new assessment workflow
   - Monitor server logs in real-time

2. **Verify Stage 1 Logging (Form Generation)**
   - Look for log entries with `event_type: "stage_start"`
   - Verify correlation_id format: `workflow_{uuid}`
   - Check stage-specific data: certification_profile, resource_count

3. **Verify Stage 2 Logging (Response Collection)**
   - Progress workflow to response collection
   - Trigger response polling
   - Look for `event_type: "polling_attempt"` logs
   - Verify datetime_format_detected field

4. **Test Manual Trigger Logging**
   - Use manual processing endpoint
   - Verify `event_type: "manual_trigger"` logs
   - Check trigger_reason and user_action fields

5. **Verify Log Structure**
   ```json
   {
     "timestamp": "2025-09-28T15:30:00Z",
     "level": "INFO",
     "correlation_id": "workflow_12345",
     "event_type": "stage_start",
     "stage": "form_generation",
     "certification_profile": "aws-ml-cert-id",
     "resource_count": 3
   }
   ```

#### Expected Results
- ✅ All workflow stages generate structured logs
- ✅ Correlation IDs consistent across stages
- ✅ Event types properly categorized
- ✅ Stage-specific metadata captured
- ✅ Manual triggers logged with context

#### Failure Conditions
- ❌ Missing or inconsistent correlation IDs
- ❌ Unstructured log entries
- ❌ Missing stage-specific metadata

---

## Test 5: API Response Schema Validation

### Test ID: SPRINT1-005
### Priority: HIGH
### Estimated Time: 10 minutes

#### Scenario
Verify Gap Analysis API returns data matching frontend schema exactly.

#### Steps
1. **Create Test Workflow at 75%+ Progress**
   - Use manual processing to reach gap analysis stage

2. **Call Gap Analysis Endpoint**
   ```
   GET /api/v1/workflows/{workflow_id}/gap-analysis
   ```

3. **Validate Response Schema**
   - Verify all required fields present:
     - `workflow_id` (string UUID)
     - `overall_score` (number 0-100)
     - `overall_confidence` (number 0-100)
     - `overconfidence_indicator` (boolean)
     - `domain_performance` (array of objects)
     - `learning_gaps` (array of objects)
     - `bloom_taxonomy_breakdown` (array of objects)
     - `recommended_study_plan` (object)
     - `generated_at` (ISO string)

4. **Test Frontend Integration**
   - Load Gap Analysis Dashboard
   - Verify no "Failed to parse server response" errors
   - Confirm all data displays correctly

#### Expected Results
- ✅ API response matches frontend schema exactly
- ✅ All required fields present and correctly typed
- ✅ Frontend parses response without errors
- ✅ Data displays correctly in dashboard

#### Failure Conditions
- ❌ Schema validation errors
- ❌ Missing or incorrectly typed fields
- ❌ Frontend parsing failures

---

## Test Execution Checklist

### Before Testing
- [ ] Test environment set up correctly
- [ ] Fresh database state (or documented state)
- [ ] Both frontend and backend servers running
- [ ] Test data prepared

### During Testing
- [ ] Record all test results
- [ ] Screenshot any UI issues
- [ ] Save relevant log entries
- [ ] Note performance observations

### After Testing
- [ ] All tests executed
- [ ] Results documented
- [ ] Critical issues resolved before Sprint 1 completion
- [ ] Test environment cleaned up

## Test Result Template

```
Test ID: SPRINT1-XXX
Date/Time:
Tester:
Environment:

PASS/FAIL:

Results:
- Step 1: PASS/FAIL - Notes
- Step 2: PASS/FAIL - Notes
- Step 3: PASS/FAIL - Notes

Issues Found:
- Issue 1: Description
- Issue 2: Description

Performance Notes:
- Response times
- UI responsiveness
- Log volume/clarity

Overall Assessment: PASS/FAIL
Required Actions:
```

## Success Criteria

**Sprint 1 is complete when:**
1. ✅ All CRITICAL tests pass (Tests 1, 2, 3)
2. ✅ All HIGH priority tests pass (Tests 4, 5)
3. ✅ No blocking issues remain
4. ✅ Enhanced logging operational
5. ✅ System stable for Sprint 2 development

**Definition of Done:**
- All manual tests documented and passed
- Critical bugs fixed and verified
- Enhanced logging confirmed working
- System ready for next development phase