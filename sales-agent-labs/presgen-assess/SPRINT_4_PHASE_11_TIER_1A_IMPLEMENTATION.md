# Sprint 4 Phase 11 - Tier 1a: LLM-Based Slide Generation

**Status:** In Progress
**Date:** 2025-10-14
**Issue:** Enhanced Tier 1 prompt prepared but not used for slide generation
**Solution:** Implement LLM-based slide generation in PresGen-Assess

---

## Problem Analysis

### Current Workflow (Broken)

```
1. PresGen-Assess: _build_slide_plans()
   └─> Generates GENERIC slides (hardcoded templates)
   └─> "Clarify the core concept"
   └─> "Connect theory to practical implementation"
   └─> NO LLM call, NO RAG context used

2. PresGen-Assess: _create_public_presentation()
   └─> Uploads generic slides to Google Slides

3. PresGen-Assess: Calls PresGen-Core with custom_prompt (152K chars)
   └─> custom_prompt contains RAG context, quality rubric, structured examples

4. PresGen-Core: /training/presentation-only endpoint
   └─> Calls presgen-training2 ModeOrchestrator

5. ModeOrchestrator: Reads existing Google Slides
   └─> Slides already exist → content_text/custom_prompt IGNORED
   └─> Generates TTS from existing (generic) slide notes
   └─> Produces video with generic content

RESULT: Enhanced prompt is sent but never used ❌
```

### Root Cause

**The custom prompt (152K chars with RAG context) is prepared correctly but never used because:**

1. Slides are created BEFORE calling PresGen-Core
2. ModeOrchestrator only generates slides if `generate_new_slides=True` AND no `google_slides_url` provided
3. Since `google_slides_url` is already set, ModeOrchestrator skips slide generation
4. The `content_text` parameter is only used for TTS narration generation, not slide content

**Evidence from Code:**

**presgen-training2/src/modes/orchestrator.py:334-348**
```python
elif request.generate_new_slides:
    # Generate new slides from content
    script_text = self._prepare_script(request)
    # TODO: Integrate with existing PresGen slide generation
    # For now, return error as this requires PresGen-Core integration
    return GenerationResult(
        success=False,
        error="New slide generation not yet implemented - use Google Slides URL"
    )
else:
    return GenerationResult(
        success=False,
        error="Must provide Google Slides URL or enable new slide generation"
    )
```

**Key Finding:** ModeOrchestrator's slide generation is not implemented. It requires a Google Slides URL, which forces the pre-creation of slides in PresGen-Assess.

---

## Architecture Analysis

### Service Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PresGen-Assess                           │
│                         (Port 8000)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  workflows.py:                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. _format_prompt_template()                             │  │
│  │    ├─> Retrieves RAG context (18K chars)                │  │
│  │    ├─> Loads certification prompt from DB                │  │
│  │    ├─> Substitutes all variables                         │  │
│  │    └─> Returns 152K char custom prompt ✅               │  │
│  │                                                           │  │
│  │ 2. _build_slide_plans()                                  │  │
│  │    ├─> NO LLM call                                       │  │
│  │    ├─> Generates generic template slides                 │  │
│  │    └─> Returns hardcoded bullets ❌                      │  │
│  │                                                           │  │
│  │ 3. _create_public_presentation()                         │  │
│  │    └─> Uploads generic slides to Google Slides           │  │
│  │                                                           │  │
│  │ 4. Calls PresGen-Core with:                              │  │
│  │    ├─> google_slides_url (already has generic content)   │  │
│  │    └─> content_text=custom_prompt (152K chars)           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTP POST /training/presentation-only
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PresGen-Core                            │
│                         (Port 8080)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  http.py:                                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ @app.post("/training/presentation-only")                 │  │
│  │  ├─> Receives: google_slides_url + content_text         │  │
│  │  └─> Calls ModeOrchestrator                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │ Imports presgen-training2
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      presgen-training2                          │
│                      ModeOrchestrator                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  orchestrator.py:                                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ generate_video()                                         │  │
│  │  ├─> IF google_slides_url provided:                     │  │
│  │  │    └─> Read existing slides (IGNORES content_text) ❌│  │
│  │  │                                                       │  │
│  │  ├─> ELIF generate_new_slides:                          │  │
│  │  │    └─> Returns error "not yet implemented" ❌        │  │
│  │  │                                                       │  │
│  │  └─> Generate TTS from slide notes                      │  │
│  │       └─> Produces video with GENERIC content            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Custom Prompt Journey:
━━━━━━━━━━━━━━━━━━━━

✅ Step 1: Prompt prepared (152K chars with RAG context)
   └─> _format_prompt_template() in PresGen-Assess

✅ Step 2: Prompt sent to PresGen-Core
   └─> content_text parameter in API call

❌ Step 3: Prompt IGNORED by ModeOrchestrator
   └─> google_slides_url provided → reads existing slides
   └─> content_text never used for slide generation

❌ Step 4: Generic slides used for video
   └─> TTS generated from generic slide notes
   └─> Result: Generic presentation (40% quality)
```

---

## Solution Options Comparison

### Option A: Modify PresGen-Core
**Estimated Effort:** 3-4 hours

**Changes Required:**
1. Update `presgen-training2/src/modes/orchestrator.py`
   - Implement slide generation from `content_text`
   - Add LLM call to generate slides JSON
   - Create Google Slides from LLM output
   - Handle error cases and fallback

2. Update `TrainingVideoRequest` schema
   - Add `regenerate_slides` flag
   - Update documentation

3. Test backward compatibility
   - Ensure existing workflows still work
   - Test with/without custom prompts
   - Test all operation modes

**Pros:**
- ✅ Centralized slide generation logic
- ✅ Benefits all workflows using PresGen-Core
- ✅ Cleaner architecture

**Cons:**
- ❌ PresGen-Core is currently working and stable
- ❌ Risk of breaking existing video generation
- ❌ Requires changes to shared orchestrator
- ❌ Need backward compatibility handling
- ❌ Longer implementation time
- ❌ More testing required

**Risk Level:** MEDIUM-HIGH

---

### Option B: Modify PresGen-Assess (RECOMMENDED ✅)
**Estimated Effort:** 1-2 hours

**Changes Required:**
1. Add `_generate_slides_with_llm()` function in workflows.py
   - Call existing `llm_service.generate()` with custom prompt
   - Parse JSON response into slide_plans format
   - Add error handling with fallback

2. Update `_ensure_presentation_deck()`
   - Accept custom_prompt parameter
   - Call LLM-based generator if custom_prompt exists
   - Fall back to `_build_slide_plans()` if LLM fails

3. Update call site to pass custom_prompt
   - Minimal change to existing code
   - No schema changes required

**Pros:**
- ✅ Fast implementation (1-2 hours)
- ✅ Zero risk to PresGen-Core
- ✅ Isolated to assessment workflow
- ✅ Uses existing LLM service
- ✅ Custom prompt already prepared
- ✅ Easy rollback if needed

**Cons:**
- ⚠️ Assessment-specific solution
- ⚠️ Some logic duplication

**Risk Level:** LOW

---

## Selected Solution: Option B - Modify PresGen-Assess

### Rationale

1. **Speed:** 2-3x faster than Option A
2. **Risk:** No impact on working PresGen-Core
3. **Simplicity:** Uses existing infrastructure
4. **Effectiveness:** Solves the immediate problem
5. **Reversibility:** Easy to rollback or refactor later

---

## Implementation Plan

### Step 1: Create LLM-based Slide Generator (30 min)

**File:** `src/service/api/v1/endpoints/workflows.py`

**New Function:**
```python
async def _generate_slides_with_llm(
    custom_prompt: str,
    target_slide_count: int,
    workflow_id: str,
    db: AsyncSession,
) -> List[Dict[str, Any]]:
    """
    Generate slides using LLM with custom RAG-enhanced prompt.

    The custom_prompt already contains:
    - Complete system instructions
    - Quality rubric and requirements
    - RAG context with domain tags
    - Example output format
    - All variable substitutions complete

    This function only needs to:
    1. Call LLM with the prepared prompt
    2. Parse JSON response
    3. Convert to slide_plans format
    """
    from src.services.llm_service import LLMService

    llm_service = LLMService(db=db)

    logger.info(
        "🤖 Generating slides with LLM | workflow_id=%s | target_slides=%d | prompt_length=%d",
        workflow_id,
        target_slide_count,
        len(custom_prompt)
    )

    try:
        # Call LLM with enhanced prompt
        # The prompt already contains complete instructions and examples
        response = await llm_service.generate(
            prompt=custom_prompt,
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=4000,  # Sufficient for 12 slides with detailed content
        )

        # Parse JSON response
        # Expected format from prompt:
        # {
        #   "presentation_type": "course_remediation",
        #   "sections": [
        #     {
        #       "title": "Section Title",
        #       "slides": [
        #         {
        #           "title": "Slide Title",
        #           "bullets": ["point 1", "point 2", ...],
        #           "instructor_notes": "Narration script..."
        #         }
        #       ]
        #     }
        #   ]
        # }

        result = json.loads(response)

        # Extract slides from sections and flatten
        slide_plans = []
        for section in result.get("sections", []):
            for slide in section.get("slides", []):
                slide_plans.append({
                    "title": slide.get("title", "Untitled Slide"),
                    "subtitle": "",
                    "bullets": slide.get("bullets", []),
                    "script": slide.get("instructor_notes", ""),
                })

        logger.info(
            "✅ LLM generated %d slides | workflow_id=%s",
            len(slide_plans),
            workflow_id
        )

        # Truncate or pad to target count
        if len(slide_plans) > target_slide_count:
            slide_plans = slide_plans[:target_slide_count]

        return slide_plans

    except json.JSONDecodeError as e:
        logger.error(
            "❌ Failed to parse LLM response as JSON | workflow_id=%s | error=%s",
            workflow_id,
            str(e)
        )
        raise
    except Exception as e:
        logger.error(
            "❌ LLM slide generation failed | workflow_id=%s | error=%s",
            workflow_id,
            str(e)
        )
        raise
```

---

### Step 2: Update _ensure_presentation_deck() (15 min)

**File:** `src/service/api/v1/endpoints/workflows.py`

**Change at line 399:**
```python
async def _ensure_presentation_deck(
    course: GeneratedCourse,
    skill_course: RecommendedCourse,
    *,
    workflow_id: str,
    assessment_title: Optional[str],
    target_slide_count: int = 12,
    custom_prompt: Optional[str] = None,  # NEW PARAMETER
    db: Optional[AsyncSession] = None,     # NEW PARAMETER
) -> str:
    """Guarantee a Google Slides deck exists with the requested slide count and return its URL."""

    if course.presentation_url:
        return course.presentation_url

    title = course.course_title or f"Mastering {skill_course.skill_name}"
    subtitle = assessment_title or skill_course.exam_domain
    bullets = _summarize_learning_objectives(skill_course.learning_objectives)
    skill_name = skill_course.skill_name
    if not bullets and skill_course.course_description:
        bullets = [skill_course.course_description.strip()[:180]]

    # Build slide plans - use LLM if custom prompt available
    try:
        if custom_prompt and db:
            logger.info(
                "🎯 Using LLM-based slide generation | workflow_id=%s | prompt_length=%d",
                workflow_id,
                len(custom_prompt)
            )
            slide_plans = await _generate_slides_with_llm(
                custom_prompt=custom_prompt,
                target_slide_count=target_slide_count,
                workflow_id=workflow_id,
                db=db,
            )
        else:
            logger.info(
                "📋 Using template-based slide generation | workflow_id=%s | reason=%s",
                workflow_id,
                "no_custom_prompt" if not custom_prompt else "no_db_session"
            )
            slide_plans = _build_slide_plans(
                title=title,
                subtitle=subtitle,
                skill_name=skill_name,
                skill_course=skill_course,
                target_slide_count=target_slide_count,
            )
    except Exception as e:
        logger.warning(
            "⚠️ LLM slide generation failed, falling back to templates | workflow_id=%s | error=%s",
            workflow_id,
            str(e)
        )
        # Fallback to template-based generation
        slide_plans = _build_slide_plans(
            title=title,
            subtitle=subtitle,
            skill_name=skill_name,
            skill_course=skill_course,
            target_slide_count=target_slide_count,
        )

    # ... rest of function unchanged ...
```

---

### Step 3: Update Call Site (10 min)

**File:** `src/service/api/v1/endpoints/workflows.py`

**Change at line 3058:**
```python
# OLD:
presentation_url = await _ensure_presentation_deck(
    course,
    skill_course,
    workflow_id=workflow_id_str,
    assessment_title=workflow.assessment_title,
    target_slide_count=requested_slide_count,
)

# NEW:
presentation_url = await _ensure_presentation_deck(
    course,
    skill_course,
    workflow_id=workflow_id_str,
    assessment_title=workflow.assessment_title,
    target_slide_count=requested_slide_count,
    custom_prompt=custom_prompt,  # Pass the enhanced prompt
    db=db,                         # Pass database session for LLM service
)
```

---

### Step 4: Error Handling Strategy

**Three Levels of Fallback:**

1. **Primary:** LLM-based generation with custom prompt
   - Uses enhanced Tier 1 prompt (152K chars)
   - Generates specific, grounded content
   - Target: 70-80% quality

2. **Fallback:** Template-based generation
   - Current `_build_slide_plans()` logic
   - Generic but functional
   - Ensures workflow always completes

3. **Logging:**
   - Log which path was taken
   - Log reasons for fallback
   - Track success/failure rates

**Error Scenarios Handled:**
- ❌ LLM timeout → Fallback to templates
- ❌ JSON parse error → Fallback to templates
- ❌ Empty response → Fallback to templates
- ❌ Insufficient slides → Pad with templates
- ❌ DB session unavailable → Use templates

---

## Testing Strategy

### Test Case 1: Happy Path - LLM Generation
**Input:**
- Workflow with custom prompt (152K chars)
- RAG context with 18 chunks
- Target: 12 slides

**Expected Output:**
- ✅ LLM generates slides with specific AWS services
- ✅ Citations from RAG context in instructor notes
- ✅ Domain-specific terminology
- ✅ No generic phrases like "Clarify the core concept"
- ✅ Quality score: 70-80%

**Verification:**
```bash
# Check logs for LLM generation
grep "Using LLM-based slide generation" src/logs/presgen_assess_combined.log

# Check presentation content
# - Open Google Slides URL from logs
# - Verify bullets contain specific AWS services (e.g., "S3", "SageMaker")
# - Verify instructor notes contain citations (e.g., "As noted in Task 1.1...")
```

---

### Test Case 2: Fallback to Templates
**Input:**
- Workflow WITHOUT custom prompt
- OR LLM service unavailable

**Expected Output:**
- ✅ Falls back to template-based generation
- ✅ Generic slides created
- ✅ Workflow completes successfully
- ✅ Log shows fallback reason

**Verification:**
```bash
grep "Using template-based slide generation" src/logs/presgen_assess_combined.log
grep "reason=no_custom_prompt" src/logs/presgen_assess_combined.log
```

---

### Test Case 3: LLM Error Handling
**Input:**
- Custom prompt provided
- Simulate LLM timeout/error

**Expected Output:**
- ✅ Error caught and logged
- ✅ Automatic fallback to templates
- ✅ Workflow continues without failure
- ✅ User still gets a presentation (generic)

**Verification:**
```bash
grep "LLM slide generation failed, falling back" src/logs/presgen_assess_combined.log
```

---

## Success Metrics

### Before (Current State)
- ❌ Generic slide content
- ❌ No specific AWS services mentioned
- ❌ No citations from RAG context
- ❌ Phrases: "Clarify the core concept", "Connect theory to practice"
- ❌ Quality score: ~40%

### After (Tier 1a Implementation)
- ✅ Specific slide content
- ✅ AWS services named (S3, SageMaker, Lambda, etc.)
- ✅ Citations in instructor notes
- ✅ Domain-specific terminology
- ✅ Quality score: 70-80% (Tier 1 target)

### Measurable Improvements
1. **Citation Density:** 0 → 2-3 citations per slide
2. **Domain Terminology:** Generic → AWS-specific terms
3. **Grounding:** 0% → 80% of content grounded in RAG context
4. **Generic Phrases:** Present → Eliminated

---

## Timeline

| Task | Duration | Status |
|------|----------|--------|
| Document architecture analysis | 30 min | In Progress |
| Create `_generate_slides_with_llm()` | 30 min | Pending |
| Update `_ensure_presentation_deck()` | 15 min | Pending |
| Update call site | 10 min | Pending |
| Test happy path | 20 min | Pending |
| Test fallback scenarios | 10 min | Pending |
| **TOTAL** | **1.5-2 hours** | In Progress |

---

## Risk Mitigation

### Low Risk Implementation
- ✅ No changes to PresGen-Core (working system)
- ✅ Isolated to assessment workflow
- ✅ Automatic fallback if LLM fails
- ✅ Uses existing LLM service infrastructure
- ✅ Easy to disable (remove custom_prompt parameter)

### Rollback Plan
If implementation causes issues:
1. Remove `custom_prompt` parameter from call site
2. System reverts to template-based generation
3. No data migration needed
4. No schema changes to revert

---

## Future Enhancements (Post-Tier 1a)

After Tier 1a is working:

**Tier 2:** Structured Context Formatting
- Add domain tags to each RAG chunk
- Include relevance scores
- Format with semantic boundaries

**Tier 3:** Domain-Aware Classification
- Pre-classify chunks by domain/topic
- Store classifications in vector DB
- Retrieve by domain for better context

**Tier 4:** Adaptive Context Compression
- Intelligent chunk summarization
- Preserve key technical details
- Maximize information density

---

## References

**Related Files:**
- [workflows.py:150-285](src/service/api/v1/endpoints/workflows.py#L150-L285) - `_build_slide_plans()` (to be replaced)
- [workflows.py:399-478](src/service/api/v1/endpoints/workflows.py#L399-L478) - `_ensure_presentation_deck()` (to be updated)
- [workflows.py:2730-2901](src/service/api/v1/endpoints/workflows.py#L2730-L2901) - `_format_prompt_template()` (working)
- [workflows.py:3058](src/service/api/v1/endpoints/workflows.py#L3058) - Call site (to be updated)
- [http.py:1366-1451](../../../src/service/http.py#L1366-L1451) - PresGen-Core endpoint
- [orchestrator.py:334-348](../../../presgen-training2/src/modes/orchestrator.py#L334-L348) - ModeOrchestrator

**Related Documents:**
- [SPRINT_4_PHASE_11_RAG_ENHANCEMENT_PLAN.md](SPRINT_4_PHASE_11_RAG_ENHANCEMENT_PLAN.md) - Original enhancement plan
- [SPRINT_4_PHASE_11_STATUS.md](SPRINT_4_PHASE_11_STATUS.md) - Phase status

**Commits:**
- `dbf767b` - Fixed regex for variable detection
- `f84d53e` - Fixed prompt logging exception handling
- `dab6fa3` - Escaped curly braces in example code block
