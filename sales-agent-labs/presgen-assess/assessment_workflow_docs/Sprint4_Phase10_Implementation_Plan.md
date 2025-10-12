# Sprint 4 – Phase 10: Enhanced Logging & Validation Implementation Plan

**Created**: 2025-10-12
**Sprint**: Sprint 4 – PresGen-Avatar Integration
**Status**: 🚧 **IN PROGRESS** – Planning Complete, Implementation Starting
**Priority**: HIGH – Critical for traceability and validation

---

## 📋 Executive Summary

Phase 10 addresses critical observability and validation gaps in the course generation pipeline. While Phase 9 successfully implemented the PresGen-Core HTTP integration, **insufficient logging prevents tracing**:
- What data is sent to the LLM and what comes back
- How RAG context filters and enriches course content
- Whether presentation prompt variables resolve correctly
- What final payload PresGen-Core receives

This phase implements comprehensive logging to enable full pipeline traceability and validate that course outlines are enriched with RAG context (not based solely on Gap Analysis recommendations).

---

## 🎯 Objectives

### Primary Goals
1. **Complete LLM Observability**: Log full request prompts and response JSON
2. **RAG Context Traceability**: Show which content was retrieved and why
3. **Variable Mapping Validation**: Verify all `{variables}` in prompts resolve correctly
4. **PresGen-Core Payload Transparency**: Log complete slide content sent to Core

### Success Criteria
- ✅ All LLM requests show complete prompt text with substituted variables
- ✅ All LLM responses show raw JSON and token usage
- ✅ RAG retrieval logs show citations, relevance scores, and filtered content
- ✅ Presentation prompt shows before/after variable substitution
- ✅ PresGen-Core payload shows all slides with bullets and instructor notes
- ✅ No unresolved `{variable}` placeholders remain in prompts

---

## 📊 Current Implementation Status

### ✅ Completed (Phase 10 Report)
- Feature flag support (`PRESGEN_REGENERATE_COURSE_OUTLINE`)
- `LLMService.generate_refined_course_outline()` method
- Integration into `generate_skill_course` workflow
- Basic `COURSE_OUTLINE_REGENERATED` logging event
- Outline persistence to `RecommendedCourse` table

### ⚠️ Critical Gaps Identified

#### Gap 1: Insufficient LLM Logging
**Current State**: Only metadata logged (character counts, slide counts)
**Missing**:
- ❌ Raw prompt text sent to LLM
- ❌ Complete LLM response JSON
- ❌ Token usage per request (prompt_tokens, completion_tokens)
- ❌ Model parameters (temperature, max_tokens, finish_reason)

**Location**: [src/services/llm_service.py:391-425](../src/services/llm_service.py#L391-425)

#### Gap 2: Missing RAG Context Logging
**Current State**: No visibility into content retrieval
**Missing**:
- ❌ Which transcript chunks were selected
- ❌ Relevance scores for retrieved content
- ❌ Citation sources used
- ❌ Full RAG context text sent to LLM

**Location**: [src/services/presentation_service.py:147-150](../src/services/presentation_service.py#L147-150)

#### Gap 3: No Variable Mapping Validation
**Current State**: Prompt variables like `{course_record.skill_name}` are substituted invisibly
**Missing**:
- ❌ Log of variable mappings before substitution
- ❌ Verification that all variables resolved
- ❌ Detection of unresolved placeholders
- ❌ Actual values substituted into prompt

**Location**: [src/services/llm_service.py:382-389](../src/services/llm_service.py#L382-389)

#### Gap 4: Incomplete PresGen-Core Payload Logging
**Current State**: Only metadata logged (slide count, skill name)
**Missing**:
- ❌ Complete slide array with bullets
- ❌ Instructor notes for each slide
- ❌ Full sections structure
- ❌ HTTP request/response to PresGen-Core

**Location**: [src/service/api/v1/endpoints/workflows.py:433](../src/service/api/v1/endpoints/workflows.py#L433)

---

## 🛠️ Implementation Plan

### Phase 10.1: Enhanced LLM Request/Response Logging

**Priority**: HIGH
**Duration**: 2 hours
**Files**: [src/services/llm_service.py](../src/services/llm_service.py)

#### Task 1.1: Add Full Prompt Logging ⏳
**Objective**: Log complete prompt text sent to LLM

**Implementation**:
```python
# File: src/services/llm_service.py
# Location: Lines 391-398 (before API call)

self._log_llm_event(
    "refined_outline_request_full",
    {
        "model": self.model,
        "temperature": 0.7,
        "max_tokens": 4000,
        "prompt_text": prompt,  # ✅ NEW: Full prompt
        "recommended_course": recommended_course,  # ✅ NEW: Input data
        "rag_context_preview": rag_context[:500] + "...",  # ✅ NEW: Context sample
        "gap_analysis_summary": gap_analysis,  # ✅ NEW: Gap data
        "assessment_results_summary": assessment_results,  # ✅ NEW: Assessment data
        "target_slide_count": target_slide_count,
    },
)
```

**Validation**:
```bash
# After implementation, log should contain:
{
  "event": "refined_outline_request_full",
  "model": "gpt-4",
  "prompt_text": "You are an expert instructional designer...",
  "recommended_course": {"skill_name": "Data Engineering", ...},
  "target_slide_count": 10
}
```

#### Task 1.2: Add Complete Response Logging ⏳
**Objective**: Log raw LLM response and token usage

**Implementation**:
```python
# File: src/services/llm_service.py
# Location: After line 425 (after response parsing)

self._log_llm_event(
    "refined_outline_response_full",
    {
        "raw_response": response.choices[0].message.content,  # ✅ NEW: Complete response
        "parsed_outline": outline,  # ✅ NEW: Parsed JSON
        "token_usage": {  # ✅ NEW: Token metrics
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        },
        "model": response.model,
        "finish_reason": response.choices[0].finish_reason,
    },
)
```

**Validation**:
```bash
# After implementation, log should contain:
{
  "event": "refined_outline_response_full",
  "raw_response": "{\"presentation_type\": \"course_remediation\", ...}",
  "token_usage": {"prompt_tokens": 2500, "completion_tokens": 800, "total_tokens": 3300}
}
```

---

### Phase 10.2: RAG Context Collection Logging

**Priority**: HIGH
**Duration**: 3 hours
**Files**: [src/services/presentation_service.py](../src/services/presentation_service.py), [src/knowledge/base.py](../src/knowledge/base.py)

#### Task 2.1: Log RAG Retrieval Details ⏳
**Objective**: Show which content chunks were retrieved and their relevance

**Implementation**:
```python
# File: src/services/presentation_service.py
# Location: After line 150 (after _collect_rag_context)

self.logger.info(
    json.dumps({
        "event": "rag_context_collected",
        "workflow_id": str(workflow.id),
        "course_id": str(recommended_course.id),
        "skill_name": normalized_course.get("skill_name"),
        "query_used": f"{normalized_course['skill_name']} learning objectives",
        "chunks_retrieved": len(rag_citations),
        "total_chars": len(rag_context),
        "citations": [
            {
                "source": c.get("source"),
                "relevance_score": c.get("score"),
                "chunk_preview": c.get("text", "")[:100],
            }
            for c in rag_citations[:5]  # Top 5 most relevant
        ],
        "full_rag_context": rag_context,  # ✅ NEW: Complete context
    })
)
```

**Validation**:
```bash
# After implementation, log should contain:
{
  "event": "rag_context_collected",
  "skill_name": "Data Engineering",
  "chunks_retrieved": 8,
  "citations": [
    {"source": "aws-solutions-architect-transcript.txt", "relevance_score": 0.92, "chunk_preview": "..."}
  ],
  "full_rag_context": "Complete transcript content here..."
}
```

#### Task 2.2: Log Content Filtering Logic ⏳
**Objective**: Show how content is filtered by skill/difficulty

**Implementation**:
```python
# File: src/knowledge/base.py
# Location: In retrieve_context_for_assessment method (after filtering)

logger.info(
    json.dumps({
        "event": "rag_filtering_applied",
        "query": query,
        "certification_id": certification_id,
        "total_docs_searched": total_count,
        "docs_after_filter": len(filtered_docs),
        "filter_criteria": {
            "skill_name": skill_filter,
            "difficulty_level": difficulty_filter,
        },
        "sources_used": list(set(doc.get("source") for doc in filtered_docs)),
    })
)
```

---

### Phase 10.3: Presentation Prompt Variable Validation

**Priority**: CRITICAL
**Duration**: 2 hours
**Files**: [src/services/llm_service.py](../src/services/llm_service.py)

#### Task 3.1: Add Variable Mapping Logger ⏳
**Objective**: Validate all `{variables}` resolve correctly

**Current Prompt Variables** (from [course_generation.log](../logs/course_generation.log)):
```yaml
{course_record.skill_name}
{course_record.course_title}
{course_record.learning_objectives}
{course_record.content_outline}
{course_record.difficulty_level}
{course_record.estimated_duration_minutes}
{knowledge_base_context}
{slide_count}
```

**Implementation**:
```python
# File: src/services/llm_service.py
# Location: In _build_refined_outline_prompt method

def _build_refined_outline_prompt(...) -> str:
    """Build prompt with explicit variable tracking."""

    # Define variable mappings
    variable_map = {
        "course_record.skill_name": recommended_course.get("skill_name"),
        "course_record.course_title": recommended_course.get("course_title"),
        "course_record.learning_objectives": recommended_course.get("learning_objectives"),
        "course_record.content_outline": recommended_course.get("sections"),
        "course_record.difficulty_level": recommended_course.get("difficulty_level"),
        "course_record.estimated_duration_minutes": recommended_course.get("estimated_duration_minutes"),
        "knowledge_base_context": rag_context[:1000] + "...",  # Preview
        "slide_count": target_slide_count,
    }

    # ✅ NEW: Log mappings BEFORE substitution
    logger.info(
        json.dumps({
            "event": "prompt_variable_mapping",
            "variables": variable_map,
            "presentation_prompt_template": presentation_prompt[:500],
        })
    )

    # Build prompt using template
    prompt = presentation_prompt or self._get_default_presentation_prompt()

    # Perform substitutions
    for var, value in variable_map.items():
        placeholder = "{" + var + "}"
        if placeholder in prompt:
            prompt = prompt.replace(placeholder, str(value))

    # ✅ NEW: Log AFTER substitution to verify
    import re
    unresolved = re.findall(r"\{[^}]+\}", prompt)
    logger.info(
        json.dumps({
            "event": "prompt_after_substitution",
            "final_prompt_preview": prompt[:1000] + "...",
            "unresolved_placeholders": unresolved,
            "substitution_success": len(unresolved) == 0,
        })
    )

    if unresolved:
        logger.warning(f"⚠️ Unresolved variables in prompt: {unresolved}")

    return prompt
```

**Validation**:
```bash
# After implementation, logs should show:
1. Before substitution:
{
  "event": "prompt_variable_mapping",
  "variables": {"course_record.skill_name": "Data Engineering", ...}
}

2. After substitution:
{
  "event": "prompt_after_substitution",
  "unresolved_placeholders": [],
  "substitution_success": true
}
```

---

### Phase 10.4: PresGen-Core Payload Logging

**Priority**: HIGH
**Duration**: 2 hours
**Files**: [src/service/api/v1/endpoints/workflows.py](../src/service/api/v1/endpoints/workflows.py), [src/integrations/presgen_core/client.py](../src/integrations/presgen_core/client.py)

#### Task 4.1: Enhance Slide Content Logging ⏳
**Objective**: Log complete slide array sent to PresGen-Core

**Implementation**:
```python
# File: src/service/api/v1/endpoints/workflows.py
# Location: After line 433 (PRESENTATION_SLIDE_CONTENT_PREPARED event)

# Enhanced logging
log_course_event(
    "PRESENTATION_SLIDE_CONTENT_PREPARED",
    workflow_id=workflow_id,
    course_id=getattr(course, "id", "unknown"),
    skill_name=skill_course.skill_name,
    slide_count=len(slide_plans),
    slide_plans=slide_plans,  # ✅ NEW: Complete slide array
)

# ✅ NEW: Add separate detailed log
logger.info(
    json.dumps({
        "event": "presgen_core_payload_full",
        "workflow_id": workflow_id,
        "course_id": course_id,
        "presentation_title": slide_plans[0].get("title") if slide_plans else None,
        "sections": [
            {
                "title": plan.get("title"),
                "bullets": plan.get("bullets"),
                "instructor_notes": plan.get("instructor_notes"),
            }
            for plan in slide_plans
        ],
        "total_slides": len(slide_plans),
    })
)
```

**Validation**:
```bash
# After implementation, log should contain:
{
  "event": "presgen_core_payload_full",
  "sections": [
    {
      "title": "Mastering Data Engineering",
      "bullets": ["Understand core principles", "Apply best practices"],
      "instructor_notes": "Introduce the topic clearly. Narration ≤ 75 seconds."
    },
    ...
  ]
}
```

#### Task 4.2: Log PresGen-Core HTTP Request ⏳
**Objective**: Show exact HTTP request/response to PresGen-Core

**Implementation**:
```python
# File: src/integrations/presgen_core/client.py
# Location: In generate_presentation method (before/after HTTP POST)

# Before POST request
logger.info(
    json.dumps({
        "event": "presgen_core_http_request",
        "url": f"{self.base_url}/training/presentation-only",
        "method": "POST",
        "payload": {
            "mode": payload.get("mode"),
            "voice_profile_name": payload.get("voice_profile_name"),
            "google_slides_url": payload.get("google_slides_url"),
            "quality_level": payload.get("quality_level"),
            "use_cache": payload.get("use_cache"),
        },
        "headers": {"Authorization": "Bearer ***"},  # Redacted
    })
)

# After response
logger.info(
    json.dumps({
        "event": "presgen_core_http_response",
        "status_code": response.status_code,
        "response_body": response.json(),
        "processing_time_ms": duration_ms,
    })
)
```

---

### Phase 10.5: Validation Testing

**Priority**: MEDIUM
**Duration**: 5 hours
**Files**: `tests/test_phase10_logging.py` (new)

#### Task 5.1: Manual Validation Checklist ⏳

**Test Procedure**:
1. Set `PRESGEN_REGENERATE_COURSE_OUTLINE=true` in `.env`
2. Generate a course via API: `POST /api/v1/workflows/{id}/skills/{skill}/generate-course`
3. Review [logs/course_generation.log](../logs/course_generation.log)

**Validation Checklist**:
- [ ] Log contains `refined_outline_request_full` with complete prompt
- [ ] Log contains `refined_outline_response_full` with raw LLM JSON
- [ ] Log contains `rag_context_collected` with citations
- [ ] Log contains `prompt_variable_mapping` with all variable values
- [ ] Log contains `prompt_after_substitution` with no unresolved placeholders
- [ ] Log contains `presgen_core_payload_full` with complete slide array
- [ ] Log contains `presgen_core_http_request` with actual HTTP payload
- [ ] All `{variables}` are resolved (no remaining `{...}` in prompt)

#### Task 5.2: Create Automated Tests ⏳

**Test Coverage**:
```python
# File: tests/test_phase10_logging.py (new)

import pytest
import json
from unittest.mock import patch, MagicMock

async def test_llm_request_logging(db_session, capture_logs):
    """Verify complete LLM request is logged."""

    with capture_logs() as logs:
        await generate_skill_course(workflow_id, skill_id)

    # Assert LLM request log exists
    request_log = next(
        (log for log in logs if "refined_outline_request_full" in log),
        None
    )
    assert request_log is not None
    assert "prompt_text" in request_log
    assert "recommended_course" in request_log
    assert len(request_log["prompt_text"]) > 0


async def test_variable_substitution_logging(db_session, capture_logs):
    """Verify prompt variables are resolved correctly."""

    with capture_logs() as logs:
        await generate_skill_course(workflow_id, skill_id)

    # Check variable mapping log
    mapping_log = next(
        (log for log in logs if "prompt_variable_mapping" in log),
        None
    )
    assert mapping_log is not None
    assert "variables" in mapping_log
    assert "course_record.skill_name" in mapping_log["variables"]

    # Check substitution result
    substitution_log = next(
        (log for log in logs if "prompt_after_substitution" in log),
        None
    )
    assert substitution_log is not None
    assert substitution_log["unresolved_placeholders"] == []
    assert substitution_log["substitution_success"] is True


async def test_rag_context_logging(db_session, capture_logs):
    """Verify RAG context retrieval is logged."""

    with capture_logs() as logs:
        await generate_skill_course(workflow_id, skill_id)

    rag_log = next(
        (log for log in logs if "rag_context_collected" in log),
        None
    )
    assert rag_log is not None
    assert "chunks_retrieved" in rag_log
    assert "citations" in rag_log
    assert "full_rag_context" in rag_log
    assert len(rag_log["full_rag_context"]) > 0


async def test_presgen_core_payload_logging(db_session, capture_logs):
    """Verify complete PresGen-Core payload is logged."""

    with capture_logs() as logs:
        await generate_skill_course(workflow_id, skill_id)

    payload_log = next(
        (log for log in logs if "presgen_core_payload_full" in log),
        None
    )
    assert payload_log is not None
    assert "sections" in payload_log
    assert len(payload_log["sections"]) > 0
    assert "title" in payload_log["sections"][0]
    assert "bullets" in payload_log["sections"][0]
    assert "instructor_notes" in payload_log["sections"][0]
```

---

## 📅 Implementation Timeline

| Task | Duration | Priority | Status | Owner |
|------|----------|----------|--------|-------|
| **Phase 10.1: LLM Logging** | 2 hours | HIGH | ⏳ Pending | Dev Team |
| 1.1 Full Prompt Logging | 1 hour | HIGH | ⏳ Pending | - |
| 1.2 Complete Response Logging | 1 hour | HIGH | ⏳ Pending | - |
| **Phase 10.2: RAG Logging** | 3 hours | HIGH | ⏳ Pending | Dev Team |
| 2.1 RAG Retrieval Details | 2 hours | HIGH | ⏳ Pending | - |
| 2.2 Content Filtering Logic | 1 hour | MEDIUM | ⏳ Pending | - |
| **Phase 10.3: Variable Validation** | 2 hours | CRITICAL | ⏳ Pending | Dev Team |
| 3.1 Variable Mapping Logger | 2 hours | CRITICAL | ⏳ Pending | - |
| **Phase 10.4: Payload Logging** | 2 hours | HIGH | ⏳ Pending | Dev Team |
| 4.1 Slide Content Logging | 1 hour | HIGH | ⏳ Pending | - |
| 4.2 HTTP Request Logging | 1 hour | HIGH | ⏳ Pending | - |
| **Phase 10.5: Testing** | 5 hours | MEDIUM | ⏳ Pending | QA Team |
| 5.1 Manual Validation | 2 hours | MEDIUM | ⏳ Pending | - |
| 5.2 Automated Tests | 3 hours | MEDIUM | ⏳ Pending | - |
| **Total** | **14 hours** | | | |

---

## 🎯 Key Validation Points

### 1. Presentation Prompt Variable Coverage

The presentation prompt template uses these variables (from [course_generation.log:10-163](../logs/course_generation.log#L10-163)):

| Variable | Should Map To | Current Status | Validation Method |
|----------|---------------|----------------|-------------------|
| `{course_record.skill_name}` | `skill_course.skill_name` | ❓ Not logged | Task 3.1 |
| `{course_record.learning_objectives}` | `skill_course.learning_objectives` | ❓ Not logged | Task 3.1 |
| `{course_record.content_outline}` | `skill_course.sections` | ❓ Not logged | Task 3.1 |
| `{knowledge_base_context}` | RAG retrieved context | ❓ Not logged | Task 2.1 + 3.1 |
| `{slide_count}` | `target_slide_count` | ✅ Logged | [course_generation.log:7](../logs/course_generation.log#L7) |

### 2. Course Outline vs RAG Context

**Requirement**: "Course outline sent to PresGen Core SHOULD NOT be based SOLELY on the Gap Analysis Course Recommendation."

**Validation Steps**:
1. **Task 2.1**: Verify RAG context was retrieved (log shows chunks + citations)
2. **Task 3.1**: Verify RAG context was included in LLM prompt (variable mapping log)
3. **Task 1.2**: Verify LLM response includes RAG-sourced content (response log)
4. **Task 4.1**: Verify final slides contain content from both outline AND RAG context

**Success Criteria**:
- ✅ RAG context > 0 characters
- ✅ RAG citations > 0 sources
- ✅ `{knowledge_base_context}` variable resolved with actual content
- ✅ Slide bullets reference RAG content (not just generic objectives)

---

## 📝 Remaining Work (From Phase 10 Report)

### From Original Phase 10 Report
- ⏳ Add automated tests (unit/integration) covering outline regeneration
- ⏳ Validate/adjust prompt tuning for different certification types
- ⏳ Document rollout procedure and advise ops on enabling flag
- ⏳ Monitor logs in production to refine prompt size and token usage

### New Requirements (This Plan)
- ⏳ Implement Tasks 1.1 - 4.2 (enhanced logging)
- ⏳ Execute Task 5.1 (manual validation checklist)
- ⏳ Implement Task 5.2 (automated test suite)
- ⏳ Update project status docs with implementation results

---

## 🚀 Next Steps

### Immediate Actions (This Sprint)
1. ✅ Review Phase 10 Report and current implementation
2. ✅ Create comprehensive implementation plan (this document)
3. ⏳ Update project status docs with Phase 10 plan
4. ⏳ Git commit and push Phase 10 plan
5. ⏳ Implement Task 3.1 (Variable Mapping - CRITICAL priority)
6. ⏳ Implement Task 1.1 (Full Prompt Logging)
7. ⏳ Implement Task 1.2 (Complete Response Logging)
8. ⏳ Implement Task 2.1 (RAG Retrieval Logging)
9. ⏳ Implement Task 4.1 (Slide Content Logging)
10. ⏳ Run manual validation (Task 5.1)
11. ⏳ Update project status with results

### Post-Implementation
1. Create automated test suite (Task 5.2)
2. Monitor production logs for prompt optimization
3. Document rollout procedure
4. Update operator runbooks

---

## 📚 References

- **Phase 10 Report**: [Sprint4_Phase10_Report.md](Sprint4_Phase10_Report.md)
- **Phase 9 Status**: [PHASE_9_IMPLEMENTATION_STATUS.md](PHASE_9_IMPLEMENTATION_STATUS.md)
- **Sprint 4 Plan**: [Oct5_Avatar_SPRINT_4_IMPLEMENTATION_PLAN.md](Oct5_Avatar_SPRINT_4_IMPLEMENTATION_PLAN.md)
- **Current Logs**: [logs/course_generation.log](../logs/course_generation.log)
- **LLM Service**: [src/services/llm_service.py](../src/services/llm_service.py)
- **Presentation Service**: [src/services/presentation_service.py](../src/services/presentation_service.py)
- **Workflows Endpoint**: [src/service/api/v1/endpoints/workflows.py](../src/service/api/v1/endpoints/workflows.py)

---

**Document Status**: Active Planning
**Last Updated**: 2025-10-12
**Next Review**: After Task 3.1 completion
**Owner**: Development Team
