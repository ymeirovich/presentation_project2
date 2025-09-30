# Gap Analysis → Avatar Narrated Presentations
## Detailed Sprint-by-Sprint Implementation Plan

_Last updated: 2025-09-30_

---

## 📋 **Executive Summary**

**Project Goal**: Automated pipeline from assessment request to avatar-narrated presentation generation

**Timeline**: 10 weeks (5 sprints × 2 weeks each)

**Architecture**: Build on existing Phase 1-3 foundation, integrate AI question generation, enhance Gap Analysis Dashboard, implement on-demand Google Sheets export, integrate PresGen-Core and PresGen-Avatar

**Key Principles**:
- ✅ Database-first approach (all data persisted before export)
- ✅ On-demand Google Sheets export (user-triggered)
- ✅ Comprehensive logging at every stage
- ✅ Manual TDD validation for each Sprint
- ✅ Feature flags for safe rollout

---

## 🗂️ **Sprint Overview**

| Sprint | Duration | Focus | Key Deliverables |
|--------|----------|-------|------------------|
| **0** | Week 0 | Foundation & Bug Investigation | Service contracts, feature flags, Gap Analysis API fix, logging framework |
| **1** | Weeks 1-2 | AI Question Generation + Dashboard Enhancement | AIQuestionGenerator integration, tabbed dashboard, database schema |
| **2** | Weeks 3-4 | Google Sheets Export (4-Tab On-Demand) | Export service, RAG content retrieval, sheet formatting |
| **3** | Weeks 5-6 | PresGen-Core Integration | Content orchestration, template selection, job queue, Drive organization |
| **4** | Weeks 7-8 | PresGen-Avatar Integration (Presentation-Only) | Course generation, timer tracker, video player, download functionality |
| **5** | Weeks 9-10 | Hardening, QA, Pilot Launch | Automated testing, monitoring dashboards, security review, pilot |

---

# Sprint 0: Foundation & Bug Investigation

**Duration**: Week 0 (5 days)

**Goal**: Establish solid foundation, investigate/fix critical bugs, implement feature flags and enhanced logging

---

## 🎯 **Sprint 0 Objectives**

1. **Service Contracts**: Freeze API schemas for Gap Analysis, Sheet Export, Course Generation
2. **Feature Flags**: Implement toggles for new features
3. **Bug Investigation**: Gap Analysis API parsing error
4. **Logging Framework**: Enhanced structured logging across all services
5. **Database Schema**: Prepare for Gap Analysis content storage

---

## 📦 **Sprint 0 Deliverables**

### **1. Service Contract Definitions**

```python
# src/schemas/gap_analysis.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

class SkillGap(BaseModel):
    """Individual skill gap identified in assessment."""
    skill_id: str
    skill_name: str
    exam_domain: str
    exam_subsection: Optional[str]
    severity: int = Field(..., ge=0, le=10, description="Gap severity 0-10")
    confidence_delta: float = Field(..., description="User confidence vs actual performance")
    question_ids: List[str] = Field(default_factory=list)

class GapAnalysisResult(BaseModel):
    """Complete gap analysis results."""
    workflow_id: UUID
    overall_score: float = Field(..., ge=0, le=100)
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    skill_gaps: List[SkillGap]
    performance_by_domain: Dict[str, float]
    text_summary: str
    charts_data: Dict[str, Any]
    generated_at: datetime

class ContentOutlineItem(BaseModel):
    """Content mapped to skill gap."""
    skill_id: str
    skill_name: str
    exam_domain: str
    exam_guide_section: str
    content_items: List[Dict[str, Any]]  # topic, source, page_ref, summary
    rag_retrieval_score: float

class RecommendedCourse(BaseModel):
    """Course recommendation for skill gap."""
    course_id: UUID
    course_title: str
    exam_domain: str
    skills_covered: List[Dict[str, str]]
    generation_status: str  # pending, generating, completed, failed
    video_url: Optional[str]
    download_url: Optional[str]
    duration_seconds: Optional[int]

class GoogleSheetsExportRequest(BaseModel):
    """Request to export assessment to Google Sheets."""
    workflow_id: UUID

class GoogleSheetsExportResponse(BaseModel):
    """Response after successful export."""
    success: bool
    sheet_id: str
    sheet_url: str
    tabs: List[str]
    exported_at: datetime
```

---

### **2. Feature Flag Implementation**

```python
# src/common/feature_flags.py
from functools import lru_cache
from pydantic import BaseSettings
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class FeatureFlagSettings(BaseSettings):
    """Feature flags for gradual rollout of new functionality."""

    # Sprint 1 flags
    enable_ai_question_generation: bool = False
    enable_gap_dashboard_enhancements: bool = False

    # Sprint 2 flags
    enable_sheets_export: bool = False
    enable_rag_content_retrieval: bool = False

    # Sprint 3 flags
    enable_presgen_core_integration: bool = False

    # Sprint 4 flags
    enable_presgen_avatar_integration: bool = False

    # Infrastructure flags
    enable_google_rate_limiter: bool = False  # Keep false in dev
    enable_enhanced_logging: bool = True
    enable_performance_metrics: bool = True

    class Config:
        env_prefix = "FEATURE_"
        env_file = ".env"

@lru_cache()
def get_feature_flags() -> FeatureFlagSettings:
    """Get cached feature flags instance."""
    return FeatureFlagSettings()

def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled."""
    flags = get_feature_flags()
    enabled = getattr(flags, feature_name, False)

    if enabled:
        logger.info(f"Feature '{feature_name}' is ENABLED")
    else:
        logger.debug(f"Feature '{feature_name}' is DISABLED")

    return enabled

# Usage example:
# if is_feature_enabled("enable_ai_question_generation"):
#     questions = await ai_generator.generate_questions(...)
```

---

### **3. Enhanced Logging Framework**

```python
# src/common/enhanced_logging_v2.py
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID
from contextlib import contextmanager

class StructuredLogger:
    """Enhanced structured logging with correlation IDs and performance metrics."""

    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self.correlation_id: Optional[str] = None

    @contextmanager
    def correlation_context(self, correlation_id: str):
        """Context manager for correlation ID."""
        old_correlation_id = self.correlation_id
        self.correlation_id = correlation_id
        try:
            yield self
        finally:
            self.correlation_id = old_correlation_id

    def _build_log_context(self, **kwargs) -> Dict[str, Any]:
        """Build structured log context."""
        context = {
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": self.correlation_id
        }
        context.update(kwargs)
        return context

    def log_api_request(self, endpoint: str, method: str, **kwargs):
        """Log API request."""
        context = self._build_log_context(
            event="api_request",
            endpoint=endpoint,
            method=method,
            **kwargs
        )
        self.logger.info(f"API Request: {method} {endpoint}", extra=context)

    def log_api_response(self, endpoint: str, status_code: int, duration_ms: float, **kwargs):
        """Log API response."""
        context = self._build_log_context(
            event="api_response",
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs
        )
        self.logger.info(f"API Response: {endpoint} [{status_code}] {duration_ms}ms", extra=context)

    def log_gap_analysis_start(self, workflow_id: UUID, question_count: int):
        """Log gap analysis start."""
        context = self._build_log_context(
            event="gap_analysis_start",
            workflow_id=str(workflow_id),
            question_count=question_count
        )
        self.logger.info(f"Gap Analysis started for workflow {workflow_id}", extra=context)

    def log_gap_analysis_complete(self, workflow_id: UUID, duration_ms: float, gaps_found: int):
        """Log gap analysis completion."""
        context = self._build_log_context(
            event="gap_analysis_complete",
            workflow_id=str(workflow_id),
            duration_ms=duration_ms,
            gaps_found=gaps_found
        )
        self.logger.info(f"Gap Analysis complete: {gaps_found} gaps identified in {duration_ms}ms", extra=context)

    def log_sheets_export_start(self, workflow_id: UUID):
        """Log Google Sheets export start."""
        context = self._build_log_context(
            event="sheets_export_start",
            workflow_id=str(workflow_id)
        )
        self.logger.info(f"Sheets export started for workflow {workflow_id}", extra=context)

    def log_sheets_export_complete(self, workflow_id: UUID, sheet_id: str, duration_ms: float):
        """Log Google Sheets export completion."""
        context = self._build_log_context(
            event="sheets_export_complete",
            workflow_id=str(workflow_id),
            sheet_id=sheet_id,
            duration_ms=duration_ms
        )
        self.logger.info(f"Sheets export complete: {sheet_id} ({duration_ms}ms)", extra=context)

    def log_course_generation_start(self, course_id: UUID, course_title: str):
        """Log course generation start."""
        context = self._build_log_context(
            event="course_generation_start",
            course_id=str(course_id),
            course_title=course_title
        )
        self.logger.info(f"Course generation started: {course_title}", extra=context)

    def log_course_generation_complete(self, course_id: UUID, duration_ms: float, video_url: str):
        """Log course generation completion."""
        context = self._build_log_context(
            event="course_generation_complete",
            course_id=str(course_id),
            duration_ms=duration_ms,
            video_url=video_url
        )
        self.logger.info(f"Course generation complete: {course_id} ({duration_ms}ms)", extra=context)

    def log_error(self, error_type: str, error_message: str, **kwargs):
        """Log error with context."""
        context = self._build_log_context(
            event="error",
            error_type=error_type,
            error_message=error_message,
            **kwargs
        )
        self.logger.error(f"Error [{error_type}]: {error_message}", extra=context)
```

---

### **4. Database Schema Migration**

```sql
-- migrations/sprint_0_gap_analysis_storage.sql

-- Gap Analysis Results Storage
CREATE TABLE IF NOT EXISTS gap_analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    overall_score DECIMAL(5,2) NOT NULL,
    total_questions INTEGER NOT NULL,
    correct_answers INTEGER NOT NULL,
    incorrect_answers INTEGER NOT NULL,
    skill_gaps JSONB NOT NULL DEFAULT '[]'::jsonb,
    severity_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    performance_by_domain JSONB NOT NULL DEFAULT '{}'::jsonb,
    text_summary TEXT,
    charts_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_gap_workflow ON gap_analysis_results(workflow_id);
CREATE INDEX idx_gap_created ON gap_analysis_results(created_at DESC);

-- Content Outline Storage
CREATE TABLE IF NOT EXISTS content_outlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    skill_id VARCHAR(255) NOT NULL,
    skill_name VARCHAR(500) NOT NULL,
    exam_domain VARCHAR(255) NOT NULL,
    exam_guide_section VARCHAR(500),
    exam_guide_subsection VARCHAR(500),
    content_items JSONB NOT NULL DEFAULT '[]'::jsonb,
    rag_retrieval_score DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_outline_workflow ON content_outlines(workflow_id);
CREATE INDEX idx_outline_domain ON content_outlines(exam_domain);
CREATE INDEX idx_outline_skill ON content_outlines(skill_id);

-- Recommended Courses Storage
CREATE TABLE IF NOT EXISTS recommended_courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    course_title VARCHAR(500) NOT NULL,
    exam_domain VARCHAR(255) NOT NULL,
    exam_subsections JSONB DEFAULT '[]'::jsonb,
    skills_covered JSONB NOT NULL DEFAULT '[]'::jsonb,
    generation_status VARCHAR(50) DEFAULT 'pending',
    video_url TEXT,
    download_url TEXT,
    thumbnail_url TEXT,
    duration_seconds INTEGER,
    file_size_mb DECIMAL(8,2),
    generation_started_at TIMESTAMP,
    generation_completed_at TIMESTAMP,
    error_message TEXT,
    presgen_avatar_job_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_courses_workflow ON recommended_courses(workflow_id);
CREATE INDEX idx_courses_status ON recommended_courses(generation_status);
CREATE INDEX idx_courses_domain ON recommended_courses(exam_domain);

-- Add constraints
ALTER TABLE gap_analysis_results
    ADD CONSTRAINT chk_score_range CHECK (overall_score BETWEEN 0 AND 100);

ALTER TABLE recommended_courses
    ADD CONSTRAINT chk_generation_status
    CHECK (generation_status IN ('pending', 'generating', 'completed', 'failed'));
```

---

### **5. Gap Analysis API Investigation & Fix**

```python
# src/service/api/v1/endpoints/gap_analysis.py
from fastapi import APIRouter, HTTPException, status
from uuid import UUID
from src.common.enhanced_logging_v2 import StructuredLogger
from src.schemas.gap_analysis import GapAnalysisResult
import json

router = APIRouter(tags=["Gap Analysis"])
logger = StructuredLogger(__name__)

@router.get("/workflows/{workflow_id}/gap-analysis", response_model=GapAnalysisResult)
async def get_gap_analysis(workflow_id: UUID):
    """
    Get gap analysis results for a workflow.

    FIXED: Explicit error handling for JSON serialization
    FIXED: Proper HTTP status codes for different error conditions
    FIXED: Structured logging for debugging
    """
    try:
        logger.log_api_request(
            endpoint=f"/workflows/{workflow_id}/gap-analysis",
            method="GET",
            workflow_id=str(workflow_id)
        )

        # Import here to avoid circular imports
        from src.service.database import get_db_session
        from src.models.workflow import WorkflowExecution
        from sqlalchemy import select

        async with get_db_session() as session:
            # Fetch workflow
            stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
            result = await session.execute(stmt)
            workflow = result.scalar_one_or_none()

            if not workflow:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workflow {workflow_id} not found"
                )

            # Fetch gap analysis results
            from src.models.gap_analysis import GapAnalysisResults  # Assume we create this model
            stmt = select(GapAnalysisResults).where(GapAnalysisResults.workflow_id == workflow_id)
            result = await session.execute(stmt)
            gap_analysis = result.scalar_one_or_none()

            if not gap_analysis:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Gap analysis not found for workflow {workflow_id}"
                )

            # Construct response with explicit serialization
            response_data = GapAnalysisResult(
                workflow_id=workflow_id,
                overall_score=float(gap_analysis.overall_score),
                total_questions=gap_analysis.total_questions,
                correct_answers=gap_analysis.correct_answers,
                incorrect_answers=gap_analysis.incorrect_answers,
                skill_gaps=gap_analysis.skill_gaps,  # Already JSONB
                performance_by_domain=gap_analysis.performance_by_domain,
                text_summary=gap_analysis.text_summary or "",
                charts_data=gap_analysis.charts_data or {},
                generated_at=gap_analysis.created_at
            )

            logger.log_api_response(
                endpoint=f"/workflows/{workflow_id}/gap-analysis",
                status_code=200,
                duration_ms=0  # TODO: Add timing
            )

            return response_data

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.log_error(
            error_type="json_decode_error",
            error_message=str(e),
            workflow_id=str(workflow_id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse gap analysis data: {str(e)}"
        )
    except Exception as e:
        logger.log_error(
            error_type=type(e).__name__,
            error_message=str(e),
            workflow_id=str(workflow_id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve gap analysis: {str(e)}"
        )
```

---

## 🧪 **Sprint 0 Manual TDD Procedures**

### **Test 1: Feature Flags Validation**

**Test ID**: SPRINT0-001
**Priority**: HIGH
**Duration**: 10 minutes

**Scenario**: Verify feature flags can be toggled and are respected

**Steps**:
1. Set environment variables:
   ```bash
   export FEATURE_ENABLE_AI_QUESTION_GENERATION=false
   export FEATURE_ENABLE_ENHANCED_LOGGING=true
   ```

2. Restart server and check logs:
   ```bash
   uvicorn src.service.http:app --reload --port 8081
   ```

3. Verify feature flag loading in logs:
   ```
   INFO - Feature 'enable_ai_question_generation' is DISABLED
   INFO - Feature 'enable_enhanced_logging' is ENABLED
   ```

4. Test feature gate in code:
   ```python
   from src.common.feature_flags import is_feature_enabled

   # Should return False
   assert is_feature_enabled("enable_ai_question_generation") == False

   # Should return True
   assert is_feature_enabled("enable_enhanced_logging") == True
   ```

**Expected Results**:
- ✅ Feature flags load from environment
- ✅ Disabled features are skipped
- ✅ Enabled features execute

---

### **Test 2: Enhanced Logging Validation**

**Test ID**: SPRINT0-002
**Priority**: HIGH
**Duration**: 15 minutes

**Scenario**: Verify structured logging captures correlation IDs and context

**Steps**:
1. Make API request with custom header:
   ```bash
   curl -X GET "http://localhost:8081/api/v1/workflows/123e4567-e89b-12d3-a456-426614174000/gap-analysis" \
     -H "X-Correlation-ID: test-correlation-123"
   ```

2. Check logs for structured output:
   ```bash
   tail -f logs/presgen_assess.log | grep "test-correlation-123"
   ```

3. Verify log contains:
   - Correlation ID
   - Timestamp (ISO 8601)
   - Event type
   - Request/response metadata

**Expected Log Format**:
```json
{
  "timestamp": "2025-09-30T12:00:00.000Z",
  "correlation_id": "test-correlation-123",
  "event": "api_request",
  "endpoint": "/workflows/{workflow_id}/gap-analysis",
  "method": "GET",
  "workflow_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Expected Results**:
- ✅ Correlation ID persists across request lifecycle
- ✅ All log events include structured context
- ✅ Timestamps are in UTC ISO 8601 format

---

### **Test 3: Database Schema Migration**

**Test ID**: SPRINT0-003
**Priority**: CRITICAL
**Duration**: 20 minutes

**Scenario**: Verify new tables created and constraints enforced

**Steps**:
1. Run migration:
   ```bash
   alembic upgrade head
   ```

2. Verify tables exist:
   ```sql
   SELECT table_name
   FROM information_schema.tables
   WHERE table_name IN ('gap_analysis_results', 'content_outlines', 'recommended_courses');
   ```

3. Test constraint enforcement:
   ```sql
   -- Should FAIL: score out of range
   INSERT INTO gap_analysis_results (workflow_id, overall_score, total_questions, correct_answers, incorrect_answers, skill_gaps, severity_scores, performance_by_domain)
   VALUES ('123e4567-e89b-12d3-a456-426614174000', 150, 10, 5, 5, '[]', '{}', '{}');

   -- Should SUCCEED: valid data
   INSERT INTO gap_analysis_results (workflow_id, overall_score, total_questions, correct_answers, incorrect_answers, skill_gaps, severity_scores, performance_by_domain)
   VALUES ('123e4567-e89b-12d3-a456-426614174000', 75.5, 10, 8, 2, '[]', '{}', '{}');
   ```

4. Verify indexes created:
   ```sql
   SELECT indexname FROM pg_indexes
   WHERE tablename = 'gap_analysis_results';
   ```

**Expected Results**:
- ✅ All 3 tables created
- ✅ Constraints enforced (score 0-100)
- ✅ Indexes created for performance
- ✅ Foreign keys reference workflow_executions

---

### **Test 4: Gap Analysis API Fix Validation**

**Test ID**: SPRINT0-004
**Priority**: CRITICAL
**Duration**: 25 minutes

**Scenario**: Verify Gap Analysis API returns properly serialized JSON

**Steps**:
1. Create test workflow with gap analysis data:
   ```python
   # In Python console
   from src.service.database import get_db_session
   from src.models.workflow import WorkflowExecution
   from uuid import uuid4
   import asyncio

   async def create_test_data():
       async with get_db_session() as session:
           workflow = WorkflowExecution(
               id=uuid4(),
               user_id="test_user",
               certification_profile_id=uuid4(),
               current_step="gap_analysis_complete",
               execution_status="results_analyzed"
           )
           session.add(workflow)
           await session.commit()
           return workflow.id

   workflow_id = asyncio.run(create_test_data())
   print(f"Created workflow: {workflow_id}")
   ```

2. Call Gap Analysis API:
   ```bash
   curl -X GET "http://localhost:8081/api/v1/workflows/{workflow_id}/gap-analysis" \
     -H "Content-Type: application/json"
   ```

3. Verify response is valid JSON:
   ```bash
   curl -X GET "http://localhost:8081/api/v1/workflows/{workflow_id}/gap-analysis" | jq .
   ```

4. Check logs for error handling:
   ```bash
   tail -f logs/presgen_assess.log | grep "gap_analysis"
   ```

**Expected Results**:
- ✅ API returns 200 OK with valid JSON
- ✅ Response matches GapAnalysisResult schema
- ✅ No "Failed to parse server response" errors
- ✅ Structured logging captured request/response

---

## 📊 **Sprint 0 Acceptance Criteria**

- [ ] Feature flags implemented and tested
- [ ] Enhanced structured logging framework operational
- [ ] Database schema migrated (3 new tables)
- [ ] Gap Analysis API parsing error investigated and fixed
- [ ] Service contracts documented (OpenAPI + Pydantic)
- [ ] All Sprint 0 manual tests passing
- [ ] Code reviewed and merged to main branch

---

## 🚨 **Sprint 0 Risks & Mitigations**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Database migration failures | CRITICAL | Test migrations on staging first; have rollback script ready |
| Gap Analysis API fix incomplete | HIGH | Comprehensive error handling + structured logging for debugging |
| Feature flag configuration drift | MEDIUM | Document all flags in README; validate on startup |
| Logging overhead affects performance | LOW | Make enhanced logging toggleable; async log processing |

---

**Sprint 0 Duration**: 5 days
**Sprint 0 Team**: 1 Senior Developer + 1 QA Engineer
**Sprint 0 Review**: End of Week 0

---

_Continue to Sprint 1 in next section..._