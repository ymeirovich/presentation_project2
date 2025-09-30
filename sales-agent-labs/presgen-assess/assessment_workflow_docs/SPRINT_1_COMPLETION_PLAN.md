# Sprint 1 Completion Plan: Gap Analysis Persistence & RAG Integration

**Document Version**: 1.0
**Date Created**: 2025-10-01
**Status**: ACTIVE - Implementation Required
**Owner**: Development Team

---

## 🎯 Executive Summary

Sprint 1 is **20% complete** (1/5 major features). AI Question Generation is working, but Gap Analysis persistence, RAG integration, and Course Recommendations are not implemented. This document provides a detailed implementation plan to complete Sprint 1 and unblock Sprint 2.

**Estimated Completion Time**: 17 hours (2-3 working days)

---

## 📊 Current State Analysis

### ✅ What's Working

1. **AI Question Generation Integration**
   - `AIQuestionGenerator` successfully generates contextual questions
   - Workflow API stores `generation_method` and `question_count` in parameters
   - Computed fields in `WorkflowResponse` expose metadata
   - Feature flag system operational

### ❌ What's Broken

1. **Gap Analysis Persistence** (CRITICAL)
   - `/manual-gap-analysis` endpoint returns mock data only
   - Sprint 0 tables remain empty:
     - `gap_analysis_results`: 0 rows
     - `content_outlines`: 0 rows
     - `recommended_courses`: 0 rows
   - No persistence logic implemented

2. **RAG Content Outline Integration** (HIGH)
   - No RAG retrieval for content outlines
   - `VectorDatabaseManager` not integrated with gap analysis
   - Content outline generation not implemented

3. **Recommended Courses Generation** (HIGH)
   - No course recommendation logic
   - Priority/severity scoring not implemented
   - PresGen-Avatar integration placeholder only

### ⚠️ What's Partially Working

1. **Gap Analysis Dashboard API**
   - Endpoints exist and correct: `gap_analysis_dashboard.py`
   - Schema imports fixed (was using wrong paths)
   - Cannot be tested - no data in database

---

## 🛠️ Implementation Tasks

### **Task 1: Gap Analysis Persistence Layer** ⚠️ CRITICAL PATH

**Priority**: P0 - BLOCKS EVERYTHING
**Estimated Time**: 4 hours
**Files to Modify**:
- `src/services/gap_analysis_enhanced.py`
- `src/service/api/v1/endpoints/workflows.py` (line 1072)

#### Implementation Steps:

**1.1 Add Database Persistence Method**

```python
# src/services/gap_analysis_enhanced.py

from src.models.gap_analysis import GapAnalysisResult
from src.service.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

async def analyze_and_persist_to_database(
    self,
    workflow_id: UUID,
    assessment_responses: List[Dict],
    certification_profile: Dict,
    db: AsyncSession
) -> Dict:
    """
    Perform gap analysis AND persist to Sprint 0 tables.

    Returns:
        Dict with gap_analysis_id, skill_gaps_count, text_summary
    """
    # Step 1: Calculate gap analysis metrics
    gap_results = await self._calculate_gap_metrics(assessment_responses)

    # Step 2: Generate text summary
    text_summary = self._generate_text_summary(gap_results)

    # Step 3: Generate charts data
    charts_data = self._generate_charts_data(gap_results)

    # Step 4: Persist to database
    gap_analysis_id = await self._persist_gap_analysis(
        workflow_id=workflow_id,
        certification_profile_id=certification_profile["certification_id"],
        gap_results=gap_results,
        text_summary=text_summary,
        charts_data=charts_data,
        db=db
    )

    return {
        "success": True,
        "gap_analysis_id": str(gap_analysis_id),
        "workflow_id": str(workflow_id),
        "overall_score": gap_results["overall_score"],
        "skill_gaps_count": len(gap_results["skill_gaps"]),
        "text_summary": text_summary
    }

async def _persist_gap_analysis(
    self,
    workflow_id: UUID,
    certification_profile_id: UUID,
    gap_results: Dict,
    text_summary: str,
    charts_data: Dict,
    db: AsyncSession
) -> UUID:
    """Save gap analysis to database."""

    gap_record = GapAnalysisResult(
        workflow_id=workflow_id,
        certification_profile_id=certification_profile_id,
        overall_score=gap_results["overall_score"],
        total_questions=gap_results["total_questions"],
        correct_answers=gap_results["correct_answers"],
        incorrect_answers=gap_results["incorrect_answers"],
        skill_gaps=gap_results["skill_gaps"],  # JSON
        performance_by_domain=gap_results["performance_by_domain"],  # JSON
        severity_scores=gap_results.get("severity_scores", {}),  # JSON
        text_summary=text_summary,
        charts_data=charts_data  # JSON
    )

    db.add(gap_record)
    await db.commit()
    await db.refresh(gap_record)

    logger.info(f"✅ Persisted gap analysis: {gap_record.id} for workflow {workflow_id}")

    return gap_record.id
```

**1.2 Update `/manual-gap-analysis` Endpoint**

```python
# src/service/api/v1/endpoints/workflows.py (line ~1072)

from src.services.gap_analysis_enhanced import GapAnalysisEnhancedService

@router.post("/{workflow_id}/manual-gap-analysis")
async def manual_gap_analysis_completion(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Manually complete gap analysis WITH database persistence."""

    try:
        logger.info(f"🎯 Manual gap analysis with persistence | workflow_id={workflow_id}")

        # Get workflow details
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Prepare mock assessment responses for testing
        mock_responses = _generate_mock_responses(workflow)

        cert_profile = {
            "certification_id": workflow.certification_profile_id,
            "name": "Mock Certification",
            "collection_name": "mock_collection"
        }

        # Use enhanced service with persistence
        gap_service = GapAnalysisEnhancedService()
        result = await gap_service.analyze_and_persist_to_database(
            workflow_id=workflow_id,
            assessment_responses=mock_responses,
            certification_profile=cert_profile,
            db=db
        )

        # Update workflow status
        workflow.status = "processing"
        workflow.current_step = "presentation_generation"
        workflow.progress = 85
        await db.commit()

        logger.info(f"✅ Gap analysis persisted | gap_analysis_id={result['gap_analysis_id']}")

        return {
            "success": True,
            "message": "Gap analysis completed and persisted",
            "workflow_id": str(workflow_id),
            "gap_analysis_id": result["gap_analysis_id"],
            "skill_gaps_count": result["skill_gaps_count"],
            "text_summary": result["text_summary"]
        }

    except Exception as e:
        logger.error(f"❌ Gap analysis failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gap analysis failed: {str(e)}"
        )

def _generate_mock_responses(workflow: WorkflowExecution) -> List[Dict]:
    """Generate mock assessment responses for testing."""
    return [
        {
            "question_id": f"q{i}",
            "domain": "Security",
            "skill_id": f"skill_{i}",
            "user_answer": "A",
            "correct_answer": "B" if i % 2 == 0 else "A",
            "is_correct": i % 2 != 0
        }
        for i in range(1, 6)
    ]
```

**Testing Task 1**:
```bash
# 1. Trigger gap analysis
curl -X POST http://localhost:8081/api/v1/workflows/19952bd0-9cfe-44bc-9460-c4f521caca89/manual-gap-analysis

# 2. Verify database
sqlite3 test_database.db "SELECT COUNT(*) FROM gap_analysis_results;"
# Expected: 1

# 3. Query full record
sqlite3 test_database.db "SELECT id, workflow_id, overall_score, text_summary FROM gap_analysis_results;"
```

**Acceptance Criteria**:
- ✅ Gap analysis record inserted into database
- ✅ `overall_score`, `skill_gaps`, `text_summary` populated
- ✅ Dashboard endpoint returns data

---

### **Task 2: RAG Content Outline Integration** ⚠️ HIGH PRIORITY

**Priority**: P1
**Estimated Time**: 6 hours
**Dependencies**: Task 1 complete

#### Implementation Steps:

**2.1 Verify RAG Infrastructure**

```bash
# Test if VectorDatabaseManager is available
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
source .venv/bin/activate
python -c "from src.knowledge.embeddings import VectorDatabaseManager; print('✅ RAG available')"
```

**2.2 Implement Content Outline Generation**

```python
# src/services/gap_analysis_enhanced.py

from src.models.gap_analysis import ContentOutline
from src.knowledge.embeddings import VectorDatabaseManager

async def _generate_content_outlines(
    self,
    gap_analysis_id: UUID,
    workflow_id: UUID,
    skill_gaps: List[Dict],
    certification_profile: Dict,
    db: AsyncSession
):
    """
    Generate content outlines via RAG retrieval.
    Falls back to mock content if RAG unavailable.
    """
    try:
        vector_db = VectorDatabaseManager()
        collection_name = certification_profile.get("collection_name", "")

        for gap in skill_gaps:
            try:
                # RAG Query
                query = f"{gap['skill_name']} {gap['exam_domain']}"
                rag_results = await vector_db.search(
                    collection_name=collection_name,
                    query=query,
                    n_results=5
                )

                # Format content items
                content_items = [
                    {
                        "topic": result.get("title", ""),
                        "source": result.get("source", "Exam Guide"),
                        "page_ref": result.get("page", ""),
                        "summary": result.get("content", "")[:500]
                    }
                    for result in rag_results
                ]

                rag_score = rag_results[0].get("score", 0) if rag_results else 0

            except Exception as rag_error:
                logger.warning(f"RAG retrieval failed for {gap['skill_name']}: {rag_error}")
                # Fallback to mock content
                content_items = self._generate_mock_content_items(gap)
                rag_score = 0.0

            # Persist content outline
            outline = ContentOutline(
                gap_analysis_id=gap_analysis_id,
                workflow_id=workflow_id,
                skill_id=gap["skill_id"],
                skill_name=gap["skill_name"],
                exam_domain=gap["exam_domain"],
                exam_guide_section=gap.get("exam_guide_section", ""),
                content_items=content_items,
                rag_retrieval_score=rag_score
            )

            db.add(outline)

        await db.commit()
        logger.info(f"✅ Generated {len(skill_gaps)} content outlines")

    except Exception as e:
        logger.error(f"❌ Content outline generation failed: {e}")
        await db.rollback()
        raise

def _generate_mock_content_items(self, gap: Dict) -> List[Dict]:
    """Generate mock content when RAG unavailable."""
    return [
        {
            "topic": f"Introduction to {gap['skill_name']}",
            "source": "Mock Exam Guide",
            "page_ref": "Ch. 1",
            "summary": f"Overview of {gap['skill_name']} concepts and best practices."
        },
        {
            "topic": f"Advanced {gap['skill_name']} Techniques",
            "source": "Mock Exam Guide",
            "page_ref": "Ch. 5",
            "summary": f"Deep dive into {gap['skill_name']} implementation patterns."
        }
    ]
```

**2.3 Wire Content Outlines into Main Flow**

```python
# Update analyze_and_persist_to_database() method

async def analyze_and_persist_to_database(...):
    # ... (existing gap analysis code)

    # NEW: Generate content outlines after gap analysis
    await self._generate_content_outlines(
        gap_analysis_id=gap_analysis_id,
        workflow_id=workflow_id,
        skill_gaps=gap_results["skill_gaps"],
        certification_profile=certification_profile,
        db=db
    )

    return result
```

**Testing Task 2**:
```bash
# Verify content outlines created
sqlite3 test_database.db "SELECT COUNT(*) FROM content_outlines WHERE workflow_id='19952bd09cfe44bc9460c4f521caca89';"
# Expected: 5 (one per skill gap)

# Test dashboard endpoint
curl http://localhost:8081/api/v1/gap-analysis-dashboard/workflow/19952bd0-9cfe-44bc-9460-c4f521caca89/content-outlines
```

**Acceptance Criteria**:
- ✅ Content outlines inserted into database
- ✅ RAG retrieval attempted (or mock fallback used)
- ✅ Dashboard endpoint returns content outlines

---

### **Task 3: Recommended Courses Generation** ⚠️ HIGH PRIORITY

**Priority**: P1
**Estimated Time**: 4 hours
**Dependencies**: Task 1 complete

#### Implementation Steps:

```python
# src/services/gap_analysis_enhanced.py

from src.models.gap_analysis import RecommendedCourse

async def _generate_recommended_courses(
    self,
    gap_analysis_id: UUID,
    workflow_id: UUID,
    skill_gaps: List[Dict],
    certification_profile: Dict,
    db: AsyncSession
):
    """Generate recommended PresGen-Avatar courses."""

    for idx, gap in enumerate(skill_gaps):
        # Determine course parameters based on severity
        severity = gap.get("severity", 5)

        if severity >= 8:
            difficulty = "advanced"
            duration = 120
        elif severity >= 5:
            difficulty = "intermediate"
            duration = 90
        else:
            difficulty = "beginner"
            duration = 60

        # Generate course outline
        course_outline = {
            "sections": [
                {"title": f"Introduction to {gap['skill_name']}", "duration_min": duration // 4},
                {"title": "Core Concepts", "duration_min": duration // 3},
                {"title": "Advanced Topics", "duration_min": duration // 3},
                {"title": "Practice & Review", "duration_min": duration // 6}
            ]
        }

        learning_objectives = [
            f"Understand {gap['skill_name']} fundamentals",
            f"Apply {gap['skill_name']} in real-world scenarios",
            f"Master {gap['exam_domain']} best practices"
        ]

        # Create course record
        course = RecommendedCourse(
            gap_analysis_id=gap_analysis_id,
            workflow_id=workflow_id,
            skill_id=gap["skill_id"],
            skill_name=gap["skill_name"],
            exam_domain=gap["exam_domain"],
            exam_subsection=gap.get("exam_subsection", ""),
            course_title=f"Mastering {gap['skill_name']}",
            course_description=f"Comprehensive course addressing your knowledge gap in {gap['skill_name']}. "
                              f"Designed for {difficulty} level with hands-on practice.",
            estimated_duration_minutes=duration,
            difficulty_level=difficulty,
            learning_objectives=learning_objectives,
            content_outline=course_outline,
            generation_status="pending",
            priority=int(severity)  # Higher severity = higher priority
        )

        db.add(course)

    await db.commit()
    logger.info(f"✅ Generated {len(skill_gaps)} recommended courses")
```

**Wire into Main Flow**:
```python
async def analyze_and_persist_to_database(...):
    # ... (existing code)

    # NEW: Generate recommended courses
    await self._generate_recommended_courses(
        gap_analysis_id=gap_analysis_id,
        workflow_id=workflow_id,
        skill_gaps=gap_results["skill_gaps"],
        certification_profile=certification_profile,
        db=db
    )

    return result
```

**Testing Task 3**:
```bash
# Verify courses created
sqlite3 test_database.db "SELECT COUNT(*) FROM recommended_courses WHERE workflow_id='19952bd09cfe44bc9460c4f521caca89';"
# Expected: 5

# Test dashboard endpoint
curl http://localhost:8081/api/v1/gap-analysis-dashboard/workflow/19952bd0-9cfe-44bc-9460-c4f521caca89/recommended-courses
```

**Acceptance Criteria**:
- ✅ Recommended courses inserted with priority ordering
- ✅ Course metadata (duration, difficulty) calculated
- ✅ Dashboard endpoint returns courses ordered by priority

---

### **Task 4: End-to-End Integration Testing** ⚠️ CRITICAL

**Priority**: P0
**Estimated Time**: 3 hours
**Dependencies**: Tasks 1, 2, 3 complete

#### Complete E2E Test Flow:

```bash
# Step 1: Create new workflow
curl -X POST http://localhost:8081/api/v1/workflows/ \
  -H "Content-Type: application/json" \
  -d '{
    "certification_profile_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "test_user@example.com",
    "workflow_type": "assessment_generation",
    "parameters": {"question_count": 5}
  }' | jq '.id'

# Save workflow ID
WORKFLOW_ID="<from_response>"

# Step 2: Trigger gap analysis with persistence
curl -X POST "http://localhost:8081/api/v1/workflows/${WORKFLOW_ID}/manual-gap-analysis"

# Step 3: Verify all tables populated
sqlite3 test_database.db "
SELECT
  (SELECT COUNT(*) FROM gap_analysis_results WHERE workflow_id='${WORKFLOW_ID}') as gaps,
  (SELECT COUNT(*) FROM content_outlines WHERE workflow_id='${WORKFLOW_ID}') as outlines,
  (SELECT COUNT(*) FROM recommended_courses WHERE workflow_id='${WORKFLOW_ID}') as courses;
"
# Expected: 1 | 5 | 5

# Step 4: Test all dashboard endpoints
echo "Testing Gap Analysis..."
curl "http://localhost:8081/api/v1/gap-analysis-dashboard/workflow/${WORKFLOW_ID}" | jq '.overall_score'

echo "Testing Content Outlines..."
curl "http://localhost:8081/api/v1/gap-analysis-dashboard/workflow/${WORKFLOW_ID}/content-outlines" | jq 'length'

echo "Testing Recommended Courses..."
curl "http://localhost:8081/api/v1/gap-analysis-dashboard/workflow/${WORKFLOW_ID}/recommended-courses" | jq 'length'

echo "Testing Summary..."
curl "http://localhost:8081/api/v1/gap-analysis-dashboard/workflow/${WORKFLOW_ID}/summary" | jq '.overall_score, .content_outlines_count, .recommended_courses_count'
```

**Acceptance Criteria**:
- ✅ All 3 database tables populated
- ✅ All 4 dashboard endpoints return data
- ✅ No errors in server logs
- ✅ Data relationships correct (foreign keys)

---

## 📅 Implementation Timeline

```
Day 1 (4 hours):
├─ Morning: Task 1 - Gap Analysis Persistence
│  ├─ Implement _persist_gap_analysis() method
│  ├─ Update /manual-gap-analysis endpoint
│  └─ Test and verify database records
└─ Afternoon: Testing & validation
   └─ Verify dashboard can read gap analysis

Day 2 (6 hours):
├─ Morning: Task 2 - RAG Content Outlines (4h)
│  ├─ Implement _generate_content_outlines()
│  ├─ Add RAG retrieval with mock fallback
│  └─ Test content outline persistence
└─ Afternoon: Task 3 - Recommended Courses (2h)
   ├─ Implement _generate_recommended_courses()
   ├─ Calculate priority/severity scoring
   └─ Test course persistence

Day 3 (3 hours):
└─ Task 4 - Integration & E2E Testing
   ├─ Run complete workflow test
   ├─ Validate all endpoints
   ├─ Fix any integration issues
   └─ Document Sprint 1 completion
```

**Total Effort**: ~17 hours (2-3 working days)

---

## 🚨 Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| RAG/ChromaDB unavailable | Medium | High | Mock content fallback implemented |
| Database schema mismatches | Low | Low | Using existing Sprint 0 models |
| Performance issues | Medium | Low | Add pagination if needed |
| Missing workflow data | Low | Medium | Use mock responses for testing |

---

## ✅ Definition of Done

Sprint 1 is **COMPLETE** when:

1. ✅ `/manual-gap-analysis` persists to all 3 Sprint 0 tables
2. ✅ All dashboard endpoints return data (not 404/empty)
3. ✅ RAG integration working OR mock fallback in place
4. ✅ E2E test script passes completely
5. ✅ All tests in `GAP_TO_PRES_SPRINT_1_TDD_MANUAL_TESTING.md` marked PASSED
6. ✅ Documentation updated with Sprint 1 completion status
7. ✅ Sprint 2 can begin (no blockers)

---

## 📝 Next Steps

1. **Immediate**: Assign Task 1 (Gap Analysis Persistence) - 4 hours
2. **Day 2**: Complete Tasks 2 & 3 (RAG + Courses) - 10 hours
3. **Day 3**: E2E testing and sign-off - 3 hours
4. **Then**: Update Sprint 2 plan and begin Sheets Export

---

**Document Status**: Ready for implementation
**Blockers**: None - all dependencies met
**Approval Required**: Development Lead sign-off before Task 1
