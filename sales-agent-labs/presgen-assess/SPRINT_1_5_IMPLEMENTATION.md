# Sprints 1-5: Implementation Plan
## AI Question Generation → Avatar Narrated Presentations

_Last updated: 2025-09-30_

**Prerequisites**: Sprint 0 complete (see [DETAILED_SPRINT_PLAN.md](DETAILED_SPRINT_PLAN.md))

---

# Sprint 1: AI Question Generation + Gap Analysis Dashboard Enhancement

**Duration**: Weeks 1-2
**Goal**: Integrate AI question generation, enhance Gap Analysis Dashboard with tabs, text summary, and database persistence

---

## 🎯 **Sprint 1 Objectives**

1. **AI Question Generation Integration**: Wire `AIQuestionGenerator` into workflow orchestrator
2. **Gap Analysis Dashboard UI**: Implement tabbed display (Content Outline + Recommended Courses)
3. **Text Summary Generation**: Auto-generate plain language summary of gap analysis results
4. **Chart Enhancements**: Add tooltips, side panel, interpretation guide
5. **Database Persistence**: Store all Gap Analysis data in database (not Google Sheets yet)

---

## 📦 **Sprint 1 Deliverables**

### **1. AI Question Generation Workflow Integration**

```python
# src/services/workflow_orchestrator.py - UPDATED
from src.services.ai_question_generator import AIQuestionGenerator
from src.common.feature_flags import is_feature_enabled

class WorkflowOrchestrator:
    def __init__(self):
        self.ai_question_generator = AIQuestionGenerator()
        # ... existing services

    async def execute_assessment_to_form_workflow(
        self,
        certification_profile_id: UUID,
        user_id: str,
        use_ai_generation: bool = True,  # NEW parameter
        assessment_data: Dict[str, Any] = None,
        form_settings: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute assessment-to-form workflow with optional AI question generation."""

        correlation_id = f"workflow_{certification_profile_id}"
        workflow = await self._get_or_create_workflow(
            certification_profile_id, user_id, assessment_data
        )

        try:
            # STEP 1: Generate or use provided questions
            if use_ai_generation and is_feature_enabled("enable_ai_question_generation"):
                logger.info(f"Using AI question generation for workflow {workflow.id}")

                # Generate questions using AI
                generation_result = await self.ai_question_generator.generate_contextual_assessment(
                    certification_profile_id=certification_profile_id,
                    user_profile=user_id,
                    difficulty_level=assessment_data.get("difficulty", "intermediate"),
                    domain_distribution=assessment_data.get("domain_distribution", {}),
                    question_count=assessment_data.get("question_count", 24)
                )

                if not generation_result["success"]:
                    raise Exception("AI question generation failed")

                # Use generated questions
                questions = generation_result["assessment_data"]["questions"]
                assessment_data["questions"] = questions
                assessment_data["metadata"]["generation_method"] = "ai_generated"
                assessment_data["metadata"]["quality_scores"] = generation_result["assessment_data"]["metadata"]["quality_scores"]

            else:
                logger.info(f"Using provided questions for workflow {workflow.id}")
                questions = assessment_data.get("questions", [])
                assessment_data["metadata"]["generation_method"] = "manual"

            # STEP 2: Format questions for Google Forms
            form_requests = self.assessment_mapper.build_batch_update_requests(questions)

            # STEP 3: Create Google Form
            form_result = await self.google_forms_service.create_assessment_form(
                assessment_data=assessment_data,
                form_title=self._generate_form_title(assessment_data),
                form_description=self._generate_form_description(assessment_data),
                form_settings=form_settings
            )

            # STEP 4: Update workflow state
            workflow.google_form_id = form_result["form_id"]
            workflow.assessment_data = assessment_data
            workflow.execution_status = WorkflowStatus.AWAITING_COMPLETION
            workflow.current_step = "form_deployed"

            async with get_async_session() as session:
                session.add(workflow)
                await session.commit()

            return {
                "success": True,
                "workflow_id": str(workflow.id),
                "form_id": form_result["form_id"],
                "form_url": form_result["form_url"],
                "generation_method": assessment_data["metadata"]["generation_method"],
                "question_count": len(questions),
                "status": WorkflowStatus.AWAITING_COMPLETION
            }

        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            workflow.execution_status = WorkflowStatus.ERROR
            workflow.error_message = str(e)
            raise
```

---

### **2. Enhanced Gap Analysis Service with Database Persistence**

```python
# src/services/gap_analysis_enhanced.py
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.service.database import get_db_session
from src.models.workflow import WorkflowExecution
from src.models.gap_analysis import GapAnalysisResults  # New model
from src.models.content_outline import ContentOutline  # New model
from src.models.recommended_course import RecommendedCourse  # New model
from src.common.enhanced_logging_v2 import StructuredLogger

logger = StructuredLogger(__name__)

class EnhancedGapAnalysisService:
    """Gap Analysis with database persistence and content outline generation."""

    async def analyze_and_persist(
        self,
        workflow_id: UUID,
        assessment_responses: List[Dict[str, Any]],
        certification_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform gap analysis and persist results to database.
        Returns summary for immediate display while data is saved.
        """
        start_time = datetime.utcnow()
        correlation_id = f"gap_analysis_{workflow_id}"

        logger.log_gap_analysis_start(workflow_id, len(assessment_responses))

        try:
            # STEP 1: Perform gap analysis calculations
            gap_results = await self._calculate_gaps(
                assessment_responses,
                certification_profile
            )

            # STEP 2: Generate text summary
            text_summary = await self._generate_text_summary(gap_results)

            # STEP 3: Generate charts data
            charts_data = self._build_charts_data(gap_results)

            # STEP 4: Persist gap analysis results
            async with get_db_session() as session:
                gap_record = GapAnalysisResults(
                    workflow_id=workflow_id,
                    overall_score=gap_results["overall_score"],
                    total_questions=gap_results["total_questions"],
                    correct_answers=gap_results["correct_answers"],
                    incorrect_answers=gap_results["incorrect_answers"],
                    skill_gaps=gap_results["skill_gaps"],
                    severity_scores=gap_results["severity_scores"],
                    performance_by_domain=gap_results["performance_by_domain"],
                    text_summary=text_summary,
                    charts_data=charts_data
                )
                session.add(gap_record)
                await session.commit()

            # STEP 5: Generate content outlines (RAG retrieval)
            if is_feature_enabled("enable_rag_content_retrieval"):
                await self._generate_content_outlines(
                    workflow_id,
                    gap_results["skill_gaps"],
                    certification_profile
                )

            # STEP 6: Generate recommended courses list
            await self._generate_recommended_courses(
                workflow_id,
                gap_results["skill_gaps"],
                certification_profile
            )

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.log_gap_analysis_complete(workflow_id, duration_ms, len(gap_results["skill_gaps"]))

            return {
                "success": True,
                "workflow_id": str(workflow_id),
                "overall_score": gap_results["overall_score"],
                "skill_gaps_count": len(gap_results["skill_gaps"]),
                "text_summary": text_summary,
                "charts_data": charts_data,
                "analysis_duration_ms": duration_ms
            }

        except Exception as e:
            logger.log_error("gap_analysis_failed", str(e), workflow_id=str(workflow_id))
            raise

    async def _generate_text_summary(self, gap_results: Dict[str, Any]) -> str:
        """Generate plain language summary of gap analysis results."""
        overall_score = gap_results["overall_score"]
        skill_gaps = gap_results["skill_gaps"]
        performance_by_domain = gap_results["performance_by_domain"]

        # Find strongest and weakest domains
        sorted_domains = sorted(
            performance_by_domain.items(),
            key=lambda x: x[1],
            reverse=True
        )
        strongest_domain = sorted_domains[0][0] if sorted_domains else "N/A"
        weakest_domain = sorted_domains[-1][0] if sorted_domains else "N/A"

        # Count severe gaps
        severe_gaps = [g for g in skill_gaps if g["severity"] >= 7]

        # Generate summary
        summary = f"""
You scored {overall_score:.1f}% on this assessment. Based on your results,
we identified {len(skill_gaps)} areas for improvement across {len(performance_by_domain)}
certification domains.

Your strongest performance was in {strongest_domain} ({sorted_domains[0][1]:.1f}%),
while {weakest_domain} requires additional study ({sorted_domains[-1][1]:.1f}%).

{'You have ' + str(len(severe_gaps)) + ' critical gaps that require immediate attention.' if severe_gaps else 'Most gaps are moderate and can be addressed with focused study.'}

We recommend prioritizing the topics listed in the Recommended Courses tab to address
these gaps systematically.
        """.strip()

        return summary

    async def _generate_content_outlines(
        self,
        workflow_id: UUID,
        skill_gaps: List[Dict[str, Any]],
        certification_profile: Dict[str, Any]
    ):
        """Generate content outlines by retrieving relevant content from RAG."""
        from src.knowledge.embeddings import VectorDatabaseManager

        vector_db = VectorDatabaseManager()
        collection_name = certification_profile.get("name", "")

        async with get_db_session() as session:
            for gap in skill_gaps:
                # RAG retrieval for this skill
                rag_results = await vector_db.search(
                    collection_name=collection_name,
                    query=f"{gap['skill_name']} {gap['exam_domain']}",
                    n_results=5
                )

                content_items = [
                    {
                        "topic": result.get("title", ""),
                        "source": result.get("source", ""),
                        "page_ref": result.get("page", ""),
                        "summary": result.get("content", "")[:500]
                    }
                    for result in rag_results
                ]

                outline_record = ContentOutline(
                    workflow_id=workflow_id,
                    skill_id=gap["skill_id"],
                    skill_name=gap["skill_name"],
                    exam_domain=gap["exam_domain"],
                    exam_guide_section=gap.get("exam_guide_section", ""),
                    content_items=content_items,
                    rag_retrieval_score=rag_results[0].get("score", 0) if rag_results else 0
                )
                session.add(outline_record)

            await session.commit()

    async def _generate_recommended_courses(
        self,
        workflow_id: UUID,
        skill_gaps: List[Dict[str, Any]],
        certification_profile: Dict[str, Any]
    ):
        """Generate recommended courses mapped to exam domains and skills."""
        # Group skills by domain
        domains = {}
        for gap in skill_gaps:
            domain = gap["exam_domain"]
            if domain not in domains:
                domains[domain] = []
            domains[domain].append({
                "skill_id": gap["skill_id"],
                "skill_name": gap["skill_name"]
            })

        async with get_db_session() as session:
            for domain, skills in domains.items():
                course_record = RecommendedCourse(
                    workflow_id=workflow_id,
                    course_title=f"{certification_profile['name']} - {domain} Mastery",
                    exam_domain=domain,
                    skills_covered=skills,
                    generation_status="pending"
                )
                session.add(course_record)

            await session.commit()
```

---

### **3. Gap Analysis Dashboard UI Components**

```typescript
// presgen-ui/src/components/GapAnalysisDashboard.tsx
import React, { useState, useEffect } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

interface GapAnalysisDashboardProps {
  workflowId: string;
}

export const GapAnalysisDashboard: React.FC<GapAnalysisDashboardProps> = ({ workflowId }) => {
  const [gapData, setGapData] = useState<any>(null);
  const [contentOutlines, setContentOutlines] = useState<any[]>([]);
  const [recommendedCourses, setRecommendedCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchGapAnalysisData();
  }, [workflowId]);

  const fetchGapAnalysisData = async () => {
    try {
      // Fetch gap analysis results
      const gapResponse = await fetch(`/api/v1/workflows/${workflowId}/gap-analysis`);
      const gapJson = await gapResponse.json();
      setGapData(gapJson);

      // Fetch content outlines
      const outlinesResponse = await fetch(`/api/v1/workflows/${workflowId}/content-outlines`);
      const outlinesJson = await outlinesResponse.json();
      setContentOutlines(outlinesJson);

      // Fetch recommended courses
      const coursesResponse = await fetch(`/api/v1/workflows/${workflowId}/recommended-courses`);
      const coursesJson = await coursesResponse.json();
      setRecommendedCourses(coursesJson);

      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch gap analysis data:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center p-8"><Spinner /></div>;
  }

  return (
    <div className="gap-analysis-dashboard">
      {/* Text Summary Section */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Assessment Results Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="prose max-w-none">
            <p className="text-lg leading-relaxed whitespace-pre-line">
              {gapData.text_summary}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Charts Section with Side Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
        {/* Charts - 3/4 width */}
        <div className="lg:col-span-3">
          <Card>
            <CardHeader>
              <CardTitle>Performance Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={Object.entries(gapData.performance_by_domain).map(([domain, score]) => ({
                  domain,
                  score
                }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="domain" />
                  <YAxis />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar dataKey="score" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Interpretation Panel - 1/4 width */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>How to Read These Charts</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="font-semibold text-sm mb-2">📊 Performance Bars</h4>
                <p className="text-xs text-gray-600">
                  Shows your score percentage by domain. Higher bars indicate stronger performance.
                  Hover over bars for detailed explanations.
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-sm mb-2">🎯 Target Line</h4>
                <p className="text-xs text-gray-600">
                  The red line shows the passing threshold (typically 70%). Aim to have all bars above this line.
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-sm mb-2">🔴 Critical Gaps</h4>
                <p className="text-xs text-gray-600">
                  Scores below 50% require immediate attention. Focus your study time on these areas first.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Tabbed Content: Outline + Courses */}
      <Tabs defaultValue="outline" className="w-full">
        <TabsList>
          <TabsTrigger value="outline">Content Outline</TabsTrigger>
          <TabsTrigger value="courses">Recommended Courses</TabsTrigger>
        </TabsList>

        {/* Content Outline Tab */}
        <TabsContent value="outline">
          <Card>
            <CardHeader>
              <CardTitle>Missing Skills - Detailed Content Map</CardTitle>
            </CardHeader>
            <CardContent>
              {contentOutlines.map((outline) => (
                <div key={outline.id} className="mb-6 p-4 border rounded">
                  <h4 className="font-semibold text-lg mb-2">
                    {outline.exam_domain} → {outline.skill_name}
                  </h4>
                  <p className="text-sm text-gray-600 mb-3">
                    <strong>Exam Guide Reference:</strong> {outline.exam_guide_section}
                  </p>
                  <div>
                    <p className="font-medium mb-2">Content Coverage:</p>
                    <ul className="list-disc list-inside space-y-1">
                      {outline.content_items.map((item: any, idx: number) => (
                        <li key={idx} className="text-sm">
                          {item.topic} - <em className="text-gray-500">{item.source}</em>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Recommended Courses Tab */}
        <TabsContent value="courses">
          <Card>
            <CardHeader>
              <CardTitle>Recommended Courses to Generate</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2">Course Title</th>
                    <th className="text-left p-2">Mapped Domain</th>
                    <th className="text-left p-2">Skills Covered</th>
                    <th className="text-left p-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {recommendedCourses.map((course) => (
                    <tr key={course.id} className="border-b">
                      <td className="p-2">{course.course_title}</td>
                      <td className="p-2">{course.exam_domain}</td>
                      <td className="p-2">
                        <ul className="text-sm list-disc list-inside">
                          {course.skills_covered.map((skill: any) => (
                            <li key={skill.skill_id}>{skill.skill_name}</li>
                          ))}
                        </ul>
                      </td>
                      <td className="p-2">
                        <CourseActionButton course={course} onRefresh={fetchGapAnalysisData} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

// Custom Tooltip Component
const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload) return null;

  const domain = payload[0].payload.domain;
  const score = payload[0].value;

  let interpretation = '';
  if (score >= 70) {
    interpretation = `Strong performance! You have a solid understanding of ${domain}. Continue to reinforce with practice.`;
  } else if (score >= 50) {
    interpretation = `Moderate gap. Review ${domain} concepts and practice with sample questions to improve.`;
  } else {
    interpretation = `Critical gap. ${domain} requires significant study time. Focus on fundamentals first.`;
  }

  return (
    <div className="bg-white p-3 border rounded shadow-lg max-w-xs">
      <p className="font-semibold">{domain}</p>
      <p className="text-lg">{score}%</p>
      <p className="text-sm text-gray-600 mt-2">{interpretation}</p>
    </div>
  );
};

// Course Action Button Component
const CourseActionButton: React.FC<{ course: any; onRefresh: () => void }> = ({ course, onRefresh }) => {
  const [generating, setGenerating] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (generating) {
      const interval = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [generating]);

  const handleGenerate = async () => {
    setGenerating(true);
    setElapsed(0);

    try {
      const response = await fetch(`/api/v1/courses/${course.id}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        onRefresh();
      }
    } catch (error) {
      console.error('Course generation failed:', error);
    } finally {
      setGenerating(false);
    }
  };

  if (course.generation_status === 'pending') {
    return (
      <Button onClick={handleGenerate} size="sm">
        Generate Course
      </Button>
    );
  }

  if (course.generation_status === 'generating' || generating) {
    return (
      <div className="flex items-center space-x-2">
        <Spinner className="w-4 h-4" />
        <span className="text-sm">Generating... {elapsed}s</span>
      </div>
    );
  }

  if (course.generation_status === 'completed') {
    return (
      <div className="flex space-x-2">
        <Button
          onClick={() => window.open(course.video_url, '_blank')}
          size="sm"
          variant="default"
        >
          Launch Course
        </Button>
        <Button
          onClick={() => window.open(course.download_url, '_blank')}
          size="sm"
          variant="outline"
        >
          Download
        </Button>
      </div>
    );
  }

  return <span className="text-red-500 text-sm">Failed</span>;
};
```

---

## 🧪 **Sprint 1 Manual TDD Procedures**

### **Test 1: AI Question Generation Integration**

**Test ID**: SPRINT1-001
**Priority**: CRITICAL
**Duration**: 30 minutes

**Scenario**: Verify AI question generator creates questions and integrates with workflow

**Prerequisites**:
- Feature flag `FEATURE_ENABLE_AI_QUESTION_GENERATION=true`
- Certification profile uploaded with exam guide + transcript

**Steps**:
1. Create workflow with AI generation enabled:
   ```bash
   curl -X POST "http://localhost:8081/api/v1/workflows/assessment-to-form" \
     -H "Content-Type: application/json" \
     -d '{
       "certification_profile_id": "{cert_id}",
       "user_id": "test_user",
       "use_ai_generation": true,
       "assessment_data": {
         "difficulty": "intermediate",
         "question_count": 24,
         "domain_distribution": {
           "Security": 8,
           "Networking": 8,
           "Storage": 8
         }
       }
     }'
   ```

2. Wait for workflow to complete (check logs):
   ```bash
   tail -f logs/presgen_assess.log | grep "ai_gen"
   ```

3. Verify Form created with AI-generated questions:
   ```bash
   curl -X GET "http://localhost:8081/api/v1/workflows/{workflow_id}"
   ```

4. Open Google Form URL and manually verify:
   - Question count matches requested (24)
   - Domain distribution is correct
   - Questions are relevant to certification
   - Each question mapped to exam guide skill

**Expected Results**:
- ✅ Workflow status: `awaiting_completion`
- ✅ Google Form contains 24 questions
- ✅ Questions distributed across 3 domains (8 each)
- ✅ Form metadata shows `"generation_method": "ai_generated"`
- ✅ Quality scores logged (>8.0/10)

---

### **Test 2: Gap Analysis Dashboard Display**

**Test ID**: SPRINT1-002
**Priority**: HIGH
**Duration**: 25 minutes

**Scenario**: Verify Gap Analysis Dashboard displays all components correctly

**Prerequisites**:
- Completed assessment with gap analysis results
- Database contains gap_analysis_results, content_outlines, recommended_courses

**Steps**:
1. Navigate to Gap Analysis Dashboard:
   ```
   http://localhost:3000/workflows/{workflow_id}/gap-analysis
   ```

2. Verify Text Summary displays:
   - Overall score percentage
   - Number of skill gaps
   - Strongest/weakest domains
   - Plain language recommendations

3. Verify Charts section:
   - Bar chart renders with domain scores
   - Side panel shows interpretation guide
   - Tooltip appears on hover with detailed explanation

4. Verify Tabbed Display:
   - "Content Outline" tab shows skills mapped to resources
   - "Recommended Courses" tab shows course list
   - Each course has "Generate Course" button

5. Check browser console for errors:
   ```javascript
   // Should be empty (no errors)
   ```

**Expected Results**:
- ✅ Text summary generates automatically
- ✅ Charts render without errors
- ✅ Tooltips provide context-specific explanations
- ✅ Side panel displays interpretation guide
- ✅ Both tabs load data from database
- ✅ No console errors

---

### **Test 3: Database Persistence Validation**

**Test ID**: SPRINT1-003
**Priority**: CRITICAL
**Duration**: 20 minutes

**Scenario**: Verify all gap analysis data persisted to database

**Steps**:
1. Complete an assessment workflow
2. Query database for gap analysis results:
   ```sql
   SELECT * FROM gap_analysis_results WHERE workflow_id = '{workflow_id}';
   ```

3. Verify record contains:
   - `overall_score` (0-100)
   - `skill_gaps` (JSONB array)
   - `text_summary` (not null)
   - `charts_data` (JSONB object)

4. Query content outlines:
   ```sql
   SELECT * FROM content_outlines WHERE workflow_id = '{workflow_id}';
   ```

5. Verify outlines contain:
   - Skills from gap analysis
   - RAG-retrieved content items
   - Exam guide section references

6. Query recommended courses:
   ```sql
   SELECT * FROM recommended_courses WHERE workflow_id = '{workflow_id}';
   ```

7. Verify courses contain:
   - `generation_status = 'pending'`
   - `skills_covered` (JSONB array)
   - `exam_domain` (not null)

**Expected Results**:
- ✅ Gap analysis results stored in database
- ✅ Content outlines retrieved via RAG
- ✅ Recommended courses generated per domain
- ✅ All foreign keys reference valid workflow_id

---

## 📊 **Sprint 1 Enhanced Logging Specifications**

### **AI Question Generation Logs**

```python
# When AI generation starts
logger.log_ai_generation_start(
    correlation_id=correlation_id,
    certification_profile_id=str(cert_id),
    question_count=24,
    difficulty="intermediate",
    domains=["Security", "Networking", "Storage"]
)
# Output: "AI question generation started | correlation_id=... question_count=24 difficulty=intermediate"

# When generation completes
logger.log_ai_generation_complete(
    correlation_id=correlation_id,
    questions_generated=24,
    duration_ms=5432,
    quality_scores={"relevance": 8.9, "accuracy": 9.1, "overall": 9.0},
    domain_distribution={"Security": 8, "Networking": 8, "Storage": 8}
)
# Output: "AI generation complete: 24 questions (5432ms) avg_quality=9.0"
```

### **Gap Analysis Logs**

```python
# When gap analysis starts
logger.log_gap_analysis_start(
    workflow_id=workflow_id,
    question_count=24
)
# Output: "Gap Analysis started for workflow {id} | question_count=24"

# When gap analysis completes
logger.log_gap_analysis_complete(
    workflow_id=workflow_id,
    duration_ms=2345,
    gaps_found=12
)
# Output: "Gap Analysis complete: 12 gaps identified in 2345ms"

# When content outline generated
logger.log_content_outline_generation(
    workflow_id=workflow_id,
    skill_id="sec-iam-01",
    rag_results_count=5,
    retrieval_score=0.89
)
# Output: "Content outline generated | skill=sec-iam-01 rag_results=5 score=0.89"
```

### **Dashboard Interaction Logs**

```python
# When dashboard loads
logger.log_dashboard_view(
    workflow_id=workflow_id,
    user_id=user_id,
    tab="gap_analysis"
)
# Output: "Dashboard viewed | workflow={id} tab=gap_analysis"

# When course generation triggered
logger.log_course_generation_triggered(
    course_id=course_id,
    course_title="AWS MLA - Security Mastery",
    triggered_by=user_id
)
# Output: "Course generation triggered | course={id} title='AWS MLA - Security Mastery'"
```

---

## 📋 **Sprint 1 Acceptance Criteria**

- [ ] AI Question Generator integrated into workflow orchestrator
- [ ] Feature flag controls AI generation vs manual questions
- [ ] Gap Analysis Dashboard displays text summary
- [ ] Charts include tooltips and interpretation side panel
- [ ] Tabbed display shows Content Outline + Recommended Courses
- [ ] All gap analysis data persisted to database (3 tables)
- [ ] RAG retrieval populates content outlines
- [ ] Recommended courses auto-generated per domain
- [ ] All Sprint 1 manual tests passing (3/3)
- [ ] Enhanced logging captures all major events
- [ ] Code reviewed and deployed to staging

---

**Sprint 1 Duration**: 2 weeks
**Sprint 1 Team**: 2 Senior Developers + 1 UI/UX Developer + 1 QA Engineer

---

_Continue to Sprint 2 for Google Sheets Export implementation..._

---

# Sprint 2-5 Summary (Full details in separate documents)

## Sprint 2: Google Sheets Export (4-Tab On-Demand)
- On-demand export button in Dashboard
- 4-tab sheet generation (Answers, Gap Analysis, Outline, Presentation)
- RAG content formatting for Outline tab
- Rate limiter toggle

## Sprint 3: PresGen-Core Integration
- Content orchestration service
- Template selection algorithm
- Job queue with retries
- Drive folder organization

## Sprint 4: PresGen-Avatar Integration
- Course generation from dashboard
- Timer tracker UI
- Presentation-only mode
- Video player + download

## Sprint 5: Hardening & Pilot
- Automated testing suite
- Monitoring dashboards
- Security review
- Pilot launch

---

**Total Project Duration**: 10 weeks
**Total Team**: 2-3 Senior Developers + 1 UI/UX + 1 QA + 0.5 DevOps

_For complete Sprint 2-5 details, see separate sprint documentation files._