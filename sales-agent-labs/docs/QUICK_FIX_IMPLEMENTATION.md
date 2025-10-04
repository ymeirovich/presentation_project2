# Quick Fix for Stuck Workflows - Implementation Guide

## Problem
`manual-process` endpoint (line 993 in workflows.py) only updates database, doesn't trigger actual processing.

## Solution
Replace mock data approach with real Google Forms response fetching and pipeline triggering.

## Implementation

### Step 1: Add helper function to fetch real Form responses

Add this at the top of `workflows.py` after imports:

```python
from src.services.google_forms_service import GoogleFormsService

async def fetch_form_responses_and_trigger_pipeline(
    workflow_id: UUID,
    workflow: WorkflowExecution,
    db: AsyncSession
) -> Dict[str, Any]:
    """Fetch responses from Google Forms and trigger full pipeline."""

    forms_service = GoogleFormsService()

    # 1. Fetch responses from Google Forms API
    form_id = workflow.google_form_id
    if not form_id:
        raise ValueError("No Google Form ID found in workflow")

    logger.info(f"📥 Fetching responses from Google Form {form_id}")
    responses_data = await forms_service.get_form_responses(form_id)

    responses = responses_data.get('responses', [])
    if not responses:
        raise ValueError("No responses found in Google Form")

    logger.info(f"✅ Fetched {len(responses)} responses")

    # 2. Unpause workflow
    workflow.paused_at = None
    workflow.resumed_at = datetime.utcnow()
    workflow.current_step = "gap_analysis"
    workflow.execution_status = "processing"
    workflow.progress = 50
    await db.commit()

    # 3. Trigger gap analysis with REAL responses
    from src.services.gap_analysis_enhanced import EnhancedGapAnalysisService
    gap_service = EnhancedGapAnalysisService()

    # Transform responses to expected format
    formatted_responses = []
    for response in responses:
        formatted_responses.append({
            "response_id": response.get('responseId'),
            "answers": response.get('answers', {}),
            "create_time": response.get('createTime')
        })

    # Generate gap analysis
    logger.info(f"📊 Generating gap analysis for workflow {workflow_id}")
    gap_result = await gap_service.perform_gap_analysis(
        workflow_id=workflow_id,
        certification_profile_id=workflow.certification_profile_id,
        responses=formatted_responses,
        db=db
    )

    workflow.progress = 75
    await db.commit()

    # 4. Generate content outline and recommended courses
    logger.info(f"📝 Generating content outline")
    await gap_service.generate_content_outline_for_workflow(workflow_id, db)

    logger.info(f"📚 Generating recommended courses")
    await gap_service.generate_recommended_courses_for_workflow(workflow_id, db)

    workflow.progress = 85
    workflow.current_step = "generate_presentation"
    await db.commit()

    # 5. Trigger presentation generation
    logger.info(f"🎨 Creating presentation")
    from src.services.presgen_integration_service import PresGenIntegrationService
    presgen_service = PresGenIntegrationService(db)

    presentation_result = await presgen_service.generate_presentation(
        workflow_id=workflow_id,
        assessment_title=workflow.parameters.get('title', 'Assessment'),
        user_email=workflow.user_id,
        skill_name=gap_result.get('skill_name', 'Unknown'),
        slide_count=workflow.parameters.get('slide_count', 12)
    )

    # 6. Finalize workflow
    workflow.current_step = "finalize_workflow"
    workflow.execution_status = "completed"
    workflow.progress = 100
    workflow.presentation_url = presentation_result.get('presentation_url')
    await db.commit()

    logger.info(f"✅ Workflow {workflow_id} completed successfully")

    return {
        "success": True,
        "response_count": len(responses),
        "gap_analysis_completed": True,
        "presentation_url": presentation_result.get('presentation_url')
    }
```

### Step 2: Update `manual_process_completed_form` endpoint

Replace lines 1013-1060 with:

```python
        # Fetch real responses and trigger full pipeline
        try:
            result = await fetch_form_responses_and_trigger_pipeline(
                workflow_id=workflow_id,
                workflow=workflow,
                db=db
            )

            return {
                "success": True,
                "message": "Form processing completed successfully",
                "workflow_id": str(workflow_id),
                "status": "completed",
                "current_step": "finalize_workflow",
                "response_count": result.get('response_count'),
                "presentation_url": result.get('presentation_url'),
                "mock_data_used": False
            }

        except ValueError as e:
            logger.warning(f"⚠️ Using fallback processing: {e}")
            # Fallback to existing mock approach if no responses
            workflow.current_step = "gap_analysis"
            workflow.execution_status = "processing"
            workflow.progress = 90
            await db.commit()

            return {
                "success": False,
                "message": f"No responses found: {str(e)}",
                "workflow_id": str(workflow_id),
                "note": "Please ensure the Google Form has at least one response"
            }
```

### Step 3: Add Resume endpoint

Add after `manual_process_completed_form`:

```python
@router.post("/{workflow_id}/resume")
async def resume_paused_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Resume a paused workflow."""
    try:
        logger.info(f"▶️ Resuming workflow {workflow_id}")

        # Get workflow
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Check if paused
        if not workflow.paused_at or workflow.resumed_at:
            raise HTTPException(status_code=400, detail="Workflow is not paused")

        # Resume based on current step
        if workflow.current_step in ["collect_responses", "gap_analysis"]:
            # Resume from form processing
            result = await fetch_form_responses_and_trigger_pipeline(
                workflow_id=workflow_id,
                workflow=workflow,
                db=db
            )
            return {
                "success": True,
                "message": "Workflow resumed and completed",
                "workflow_id": str(workflow_id),
                "presentation_url": result.get('presentation_url')
            }

        else:
            # Just unpause
            workflow.paused_at = None
            workflow.resumed_at = datetime.utcnow()
            workflow.execution_status = "processing"
            await db.commit()

            return {
                "success": True,
                "message": "Workflow resumed",
                "workflow_id": str(workflow_id),
                "current_step": workflow.current_step
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Resume failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Step 4: Update UI - add resumeWorkflow function

In `presgen-ui/src/lib/assess-api.ts`:

```typescript
export async function resumeWorkflow(workflowId: string): Promise<any> {
  const response = await fetch(
    `${ASSESS_API_BASE_URL}/workflows/${workflowId}/resume`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to resume workflow')
  }

  return response.json()
}
```

### Step 5: Update UI - fix handleResume

In `presgen-ui/src/components/assess/WorkflowTimeline.tsx`, replace handleResume (line 125):

```typescript
const handleResume = async () => {
  if (!workflow) return

  try {
    setResuming(true)
    // Call the NEW resume endpoint (not manual-process)
    await resumeWorkflow(workflow.id)
    onRetry?.()
    await fetchData()
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Failed to resume workflow')
  } finally {
    setResuming(false)
  }
}
```

## Testing

1. Create new assessment
2. Fill out Google Form (at least 1 response)
3. Click "Process Completed Form"
4. Watch workflow progress through stages automatically
5. Verify presentation URL appears when complete

## Rollback Plan

If this breaks, revert `workflows.py` to use the old mock approach.

The key insight: All the services already exist - we just need to call them in sequence!
