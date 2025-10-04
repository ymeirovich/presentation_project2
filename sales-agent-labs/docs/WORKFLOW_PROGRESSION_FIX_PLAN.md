# Workflow Progression Fix Plan

**Date**: 2025-10-04
**Status**: 🔴 Planning
**Priority**: Critical

## Problem Statement

Assessment workflows get stuck at various stages with no way to progress automatically or manually:

1. ❌ **Process Completed Form** button moves workflow to `gap_analysis` but doesn't trigger actual gap analysis generation
2. ❌ **Resume Workflow** button doesn't actually resume paused workflows - just calls the broken manual-process endpoint
3. ❌ **No automatic progression** from gap analysis → presentation generation
4. ❌ **Workflows remain paused** indefinitely with no way to continue

## Current Broken Flow

```
[Create Assessment]
    ↓ (auto)
[Form Created - collect_responses] ⏸️ PAUSED
    ↓ (user fills form)
[User clicks "Process Completed Form"]
    ↓ (manual-process endpoint)
[Gap Analysis stage] ⏸️ PAUSED (status changed in DB only - NO actual processing)
    ↓ ❌ STUCK HERE
[User clicks "Resume Workflow"]
    ↓ (calls manual-process again - does nothing)
[Still stuck at Gap Analysis] ⏸️ PAUSED
```

## Desired Production Flow

```
[Create Assessment]
    ↓ (auto)
[Form Created - collect_responses] ⏸️ PAUSED - waiting for responses
    ↓ (user fills form)
[User clicks "Process Completed Form"]
    ↓ (trigger full processing pipeline)
[Ingest Responses from Google Sheets] ⚙️ PROCESSING
    ↓ (auto)
[Generate Gap Analysis] ⚙️ PROCESSING
    ↓ (auto)
[Generate Content Outline] ⚙️ PROCESSING
    ↓ (auto)
[Generate Recommended Courses] ⚙️ PROCESSING
    ↓ (auto)
[Create Google Slides Presentation] ⚙️ PROCESSING
    ↓ (auto)
[Finalize Workflow] ✅ COMPLETED
```

## Fix Plan

### Phase 1: Backend - Fix Process Completed Form (Priority: CRITICAL)

**File**: `presgen-assess/src/service/api/v1/endpoints/workflows.py`

**Current Code** (lines 994-1044):
```python
@router.post("/{workflow_id}/manual-process")
async def manual_process_completed_form(...):
    # Creates mock data
    mock_responses = {...}

    # Only updates database - DOESN'T TRIGGER PROCESSING
    workflow.current_step = "gap_analysis"
    workflow.execution_status = "processing"
    await db.commit()

    return {"success": True, "message": "Manual processing initiated"}
```

**Fix Required**:
```python
@router.post("/{workflow_id}/manual-process")
async def manual_process_completed_form(
    workflow_id: UUID,
    request: ManualProcessRequest,  # NEW: Accept sheet_url
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks  # NEW: For async processing
):
    """Process completed Google Form and trigger full gap-to-presentation pipeline."""

    # 1. Unpause workflow
    workflow.paused_at = None
    workflow.resumed_at = datetime.utcnow()
    workflow.current_step = "ingest_responses"
    workflow.execution_status = "processing"
    await db.commit()

    # 2. Trigger background job for full processing
    background_tasks.add_task(
        process_form_responses_pipeline,
        workflow_id=workflow_id,
        sheet_url=request.sheet_url,
        db=db
    )

    return {
        "success": True,
        "message": "Processing pipeline started",
        "workflow_id": str(workflow_id),
        "next_steps": [
            "Ingesting responses",
            "Generating gap analysis",
            "Creating content outline",
            "Generating recommended courses",
            "Creating presentation"
        ]
    }
```

**New Background Job** (create new file):
```python
# presgen-assess/src/services/form_response_processor.py

async def process_form_responses_pipeline(
    workflow_id: UUID,
    sheet_url: str,
    db: AsyncSession
):
    """Complete pipeline: Responses → Gap Analysis → Presentation."""

    try:
        # Step 1: Ingest responses from Google Sheets
        responses = await ingest_google_sheets_responses(sheet_url)

        # Step 2: Generate gap analysis
        gap_analysis = await generate_gap_analysis(
            workflow_id=workflow_id,
            responses=responses,
            db=db
        )

        # Step 3: Generate content outline
        content_outline = await generate_content_outline(
            gap_analysis=gap_analysis,
            db=db
        )

        # Step 4: Generate recommended courses
        courses = await generate_recommended_courses(
            gap_analysis=gap_analysis,
            db=db
        )

        # Step 5: Create Google Slides presentation
        presentation = await create_presentation(
            workflow_id=workflow_id,
            gap_analysis=gap_analysis,
            content_outline=content_outline,
            db=db
        )

        # Step 6: Finalize workflow
        await finalize_workflow(
            workflow_id=workflow_id,
            presentation_url=presentation.url,
            db=db
        )

    except Exception as e:
        logger.error(f"Pipeline failed for workflow {workflow_id}: {e}")
        await mark_workflow_as_failed(workflow_id, str(e), db)
```

### Phase 2: Backend - Add Resume Workflow Endpoint (Priority: HIGH)

**File**: `presgen-assess/src/service/api/v1/endpoints/workflows.py`

**New Endpoint**:
```python
@router.post("/{workflow_id}/resume")
async def resume_paused_workflow(
    workflow_id: UUID,
    resume_request: ResumeWorkflowRequest,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks
):
    """Resume a paused workflow from any stage."""

    workflow = await get_workflow_or_404(workflow_id, db)

    # Validate workflow is paused
    if not workflow.paused_at or workflow.resumed_at:
        raise HTTPException(
            status_code=400,
            detail="Workflow is not paused"
        )

    # Unpause workflow
    workflow.paused_at = None
    workflow.resumed_at = datetime.utcnow()
    workflow.execution_status = "processing"
    await db.commit()

    # Determine next action based on current step
    if workflow.current_step == "collect_responses":
        # Resume from form completion
        background_tasks.add_task(
            process_form_responses_pipeline,
            workflow_id=workflow_id,
            sheet_url=resume_request.sheet_url,
            db=db
        )

    elif workflow.current_step == "gap_analysis":
        # Continue from gap analysis to presentation
        background_tasks.add_task(
            continue_from_gap_analysis,
            workflow_id=workflow_id,
            db=db
        )

    elif workflow.current_step == "generate_presentation":
        # Resume presentation generation
        background_tasks.add_task(
            create_presentation_from_gap_analysis,
            workflow_id=workflow_id,
            db=db
        )

    return {
        "success": True,
        "message": f"Workflow resumed from {workflow.current_step}",
        "workflow_id": str(workflow_id),
        "current_step": workflow.current_step,
        "resumed_at": workflow.resumed_at.isoformat()
    }
```

**Request Schema**:
```python
class ResumeWorkflowRequest(BaseModel):
    sheet_url: Optional[str] = None  # Required if resuming from collect_responses
    force: bool = False  # Force resume even if validation fails
```

### Phase 3: Frontend - Update Resume Workflow Button (Priority: HIGH)

**File**: `presgen-ui/src/lib/assess-api.ts`

**Add Resume API Function**:
```typescript
export async function resumeWorkflow(
  workflowId: string,
  sheetUrl?: string
): Promise<any> {
  const response = await fetch(
    `${ASSESS_API_BASE_URL}/workflows/${workflowId}/resume`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sheet_url: sheetUrl })
    }
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to resume workflow')
  }

  return response.json()
}
```

**File**: `presgen-ui/src/components/assess/WorkflowTimeline.tsx`

**Update Resume Handler** (line 125):
```typescript
const handleResume = async () => {
  if (!workflow) return

  try {
    setResuming(true)

    // If workflow is at collect_responses, prompt for sheet URL
    let sheetUrl: string | undefined
    if (workflow.current_step === 'collect_responses') {
      sheetUrl = prompt('Enter Google Sheets URL with form responses:')
      if (!sheetUrl) {
        setResuming(false)
        return
      }
    }

    // Call actual resume endpoint (not manual-process)
    await resumeWorkflow(workflow.id, sheetUrl)

    onRetry?.()
    await fetchData()
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Failed to resume workflow')
  } finally {
    setResuming(false)
  }
}
```

### Phase 4: Add Progress Tracking (Priority: MEDIUM)

**Update Background Jobs** to emit progress events:

```python
async def process_form_responses_pipeline(...):
    total_steps = 6
    current_step = 0

    async def update_progress(step_name: str):
        nonlocal current_step
        current_step += 1
        progress = int((current_step / total_steps) * 100)

        await db.execute(
            update(WorkflowExecution)
            .where(WorkflowExecution.id == workflow_id)
            .values(
                progress=progress,
                current_step=step_name
            )
        )
        await db.commit()

    await update_progress("ingest_responses")
    responses = await ingest_google_sheets_responses(sheet_url)

    await update_progress("gap_analysis")
    gap_analysis = await generate_gap_analysis(...)

    await update_progress("content_outline")
    content_outline = await generate_content_outline(...)

    await update_progress("recommended_courses")
    courses = await generate_recommended_courses(...)

    await update_progress("generate_presentation")
    presentation = await create_presentation(...)

    await update_progress("finalize_workflow")
    await finalize_workflow(...)
```

### Phase 5: Add Sheet URL Input to UI (Priority: MEDIUM)

**Update Process Completed Form Button** to prompt for sheet URL:

```typescript
const handleManualProcess = async () => {
  if (!workflow) return

  // Prompt for Google Sheets URL
  const sheetUrl = prompt(
    'Enter the Google Sheets URL containing form responses:\n\n' +
    '1. Open your Google Form\n' +
    '2. Click "Responses" tab\n' +
    '3. Click the Sheets icon\n' +
    '4. Copy the URL from the opened sheet'
  )

  if (!sheetUrl) return

  try {
    setManualProcessing(true)
    await manualProcessWorkflow(workflow.id, sheetUrl)
    onRetry?.()
    await fetchData()
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Failed to process workflow')
  } finally {
    setManualProcessing(false)
  }
}
```

## Implementation Order

### Sprint 1: Fix Critical Path (1-2 days)
1. ✅ Create `form_response_processor.py` background job
2. ✅ Fix `manual-process` endpoint to trigger pipeline
3. ✅ Add `resume` endpoint
4. ✅ Update UI Resume button to call resume endpoint
5. ✅ Test end-to-end: Form → Process → Gap Analysis → Presentation

### Sprint 2: Polish & Progress (1 day)
6. ✅ Add progress tracking to background jobs
7. ✅ Add sheet URL input to Process Form button
8. ✅ Add better error messages for each stage
9. ✅ Add retry logic for failed stages

### Sprint 3: Monitoring & Cleanup (0.5 days)
10. ✅ Add detailed logging at each pipeline stage
11. ✅ Create admin endpoint to view stuck workflows
12. ✅ Document new workflow architecture
13. ✅ Remove mock data from manual-presentation endpoint

## Files to Modify

### Backend
- ✏️ `presgen-assess/src/service/api/v1/endpoints/workflows.py` (fix manual-process, add resume)
- ✏️ `presgen-assess/src/services/form_response_processor.py` (NEW - background pipeline)
- ✏️ `presgen-assess/src/schemas/workflow.py` (add ResumeWorkflowRequest)

### Frontend
- ✏️ `presgen-ui/src/lib/assess-api.ts` (add resumeWorkflow function)
- ✏️ `presgen-ui/src/components/assess/WorkflowTimeline.tsx` (update handleResume)

### Documentation
- ✏️ `docs/WORKFLOW_ARCHITECTURE.md` (NEW - document workflow stages)
- ✏️ `docs/TROUBLESHOOTING_STUCK_WORKFLOWS.md` (NEW - admin guide)

## Success Criteria

- [x] User fills out Google Form
- [x] User clicks "Process Completed Form"
- [x] Workflow automatically progresses through:
  - [x] Ingest responses
  - [x] Generate gap analysis
  - [x] Generate content outline
  - [x] Generate recommended courses
  - [x] Create Google Slides presentation
- [x] Workflow shows as "Completed" with presentation URL
- [x] If workflow pauses, "Resume Workflow" button unpauses and continues
- [x] Progress indicator shows current stage
- [x] Errors are logged and workflow marked as failed (not stuck)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Long-running background jobs timeout | HIGH | Add task queue (Celery/Redis) |
| Database connection pool exhausted | MEDIUM | Use connection pooling, close sessions properly |
| Google API rate limits | MEDIUM | Add exponential backoff, queue system |
| Parallel workflow conflicts | LOW | Add workflow locking mechanism |

## Testing Plan

### Manual Testing
1. Create assessment → Fill form → Process → Verify completion
2. Create assessment → Fill form → Let it pause → Resume → Verify completion
3. Create assessment → Fill form → Force error → Verify workflow marked as failed
4. Create 5 assessments in parallel → Verify all complete

### Automated Testing
```python
# tests/test_workflow_progression.py

async def test_complete_workflow_pipeline():
    """Test full workflow from form to presentation."""
    # 1. Create workflow
    workflow = await create_workflow(...)

    # 2. Simulate form completion
    await simulate_form_responses(workflow.id)

    # 3. Trigger manual process
    response = await client.post(
        f"/workflows/{workflow.id}/manual-process",
        json={"sheet_url": "https://..."}
    )
    assert response.status_code == 200

    # 4. Wait for completion (with timeout)
    workflow = await poll_workflow_until_complete(workflow.id, timeout=300)

    # 5. Verify final state
    assert workflow.execution_status == "completed"
    assert workflow.current_step == "finalize_workflow"
    assert workflow.presentation_url is not None
    assert "docs.google.com/presentation" in workflow.presentation_url
```

## Next Steps

1. **Review this plan** - Confirm approach
2. **Prioritize phases** - Which to implement first?
3. **Start Sprint 1** - Fix critical path
4. **Deploy & test** - Verify workflows unstick
5. **Iterate** - Add progress tracking and polish

---

**Questions for Review**:
1. Should we use a proper task queue (Celery) or stick with FastAPI BackgroundTasks?
2. Should Resume button auto-detect sheet URL or always prompt?
3. Should we add email notifications when workflow completes?
4. Should we keep manual-presentation endpoint for testing or remove it?
