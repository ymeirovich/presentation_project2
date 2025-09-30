# Gap-to-Avatar Project Plan: Clarifications & Analysis

_Last updated: 2025-09-30_

---

## 1. AssessmentFormsMapper vs AIQuestionGenerator

### **Comparison Table**

| Aspect | AssessmentFormsMapper | AIQuestionGenerator |
|--------|----------------------|---------------------|
| **Purpose** | Format/transform pre-existing questions | Generate new questions from scratch |
| **Input** | Pre-written assessment questions (JSON/Dict) | Certification profile ID + resources + RAG knowledge base |
| **Output** | Google Forms API payload (batchUpdate requests) | Generated questions with quality metrics + source refs |
| **Intelligence** | None - pure formatting/mapping | AI-powered using RAG + LLM generation |
| **Question Source** | Manual question creation or static question bank | Dynamic generation from uploaded resources |
| **Skill Mapping** | Expects pre-mapped skills in input | Automatically maps to exam guide skills |
| **Quality Control** | No validation | Quality scoring (min 8.0/10) + validation |
| **Fallback** | N/A (requires valid input) | Sample question fallback on failure |
| **Dependencies** | None (simple utility class) | RAG Knowledge Base, LLM Service, Vector DB |
| **Use Case** | When questions are pre-authored | When questions need to be generated from resources |

### **Code Architecture**

**AssessmentFormsMapper** ([src/services/assessment_forms_mapper.py](src/services/assessment_forms_mapper.py:1)):
```python
# Simple utility class - no AI, no database
class AssessmentFormsMapper:
    def map_assessment_to_form(self, assessment_data: Dict) -> Dict:
        # Takes pre-existing questions and formats them
        questions = assessment_data.get("questions", [])
        form_items = [self._map_question_to_form_item(q) for q in questions]
        return {"info": {...}, "items": form_items}

    def build_batch_update_requests(self, questions: List[Dict]) -> List[Dict]:
        # Converts questions to Google Forms API format
        # Supports: multiple_choice, true_false, scenario, paragraph
```

**AIQuestionGenerator** ([src/services/ai_question_generator.py](src/services/ai_question_generator.py:90)):
```python
# Complex AI service - RAG + LLM + quality validation
class AIQuestionGenerator:
    def __init__(self):
        self.assessment_engine = AssessmentEngine()
        self.vector_db = VectorDatabaseManager()  # RAG
        self.prompt_service = AssessmentPromptService()

    async def generate_contextual_assessment(
        self, cert_profile_id, user_profile, difficulty,
        domain_distribution, question_count
    ) -> Dict:
        # 1. Retrieves cert resources from DB
        # 2. Generates questions per domain using RAG + LLM
        # 3. Validates quality (min score 8.0/10)
        # 4. Maps to exam guide skills automatically
        # 5. Returns questions with source references
```

### **Advantages & Disadvantages**

#### AssessmentFormsMapper ✅ ❌
**Advantages**:
- ✅ Fast - no AI processing overhead
- ✅ Simple - no external dependencies
- ✅ Predictable - same input → same output
- ✅ No cost - no LLM API calls

**Disadvantages**:
- ❌ Requires pre-written questions
- ❌ No intelligence - can't adapt to resources
- ❌ Manual skill mapping required
- ❌ No quality validation
- ❌ Can't scale without question authoring effort

#### AIQuestionGenerator ✅ ❌
**Advantages**:
- ✅ Fully automated - no manual question writing
- ✅ Resource-driven - uses uploaded exam guides/transcripts
- ✅ Quality validation - ensures 8.0/10+ scores
- ✅ Auto skill mapping - maps to exam guide taxonomy
- ✅ Scalable - generates unlimited questions
- ✅ Adaptive - personalizes to difficulty/domains

**Disadvantages**:
- ❌ Slower - AI generation takes time
- ❌ Complex - many dependencies (DB, RAG, LLM)
- ❌ Cost - LLM API usage fees
- ❌ Non-deterministic - slight variations per generation
- ❌ Requires resources - needs exam guide/transcript uploaded

### **Can They Be Merged?**

**Answer: No, but they should be composed in a pipeline.**

**Recommended Architecture**:
```
User Workflow Action
    ↓
[Option 1: AI Generation]
    → AIQuestionGenerator.generate_contextual_assessment()
    → Returns: Generated questions with metadata
    ↓
[Common Formatter]
    → AssessmentFormsMapper.build_batch_update_requests()
    → Returns: Google Forms API payload
    ↓
GoogleFormsService.create_assessment_form()

OR

[Option 2: Manual Upload]
    → User uploads pre-written questions
    → Validates format
    ↓
[Common Formatter]
    → AssessmentFormsMapper.build_batch_update_requests()
    → Returns: Google Forms API payload
    ↓
GoogleFormsService.create_assessment_form()
```

**Integration Strategy**:
1. Keep both classes separate (single responsibility principle)
2. `AIQuestionGenerator` outputs questions in same format as manual input
3. `AssessmentFormsMapper` becomes the common formatter for both paths
4. Workflow orchestrator decides which path based on user selection

---

## 2. Sprint 0 Bug Validation Status

### **Bug 1: Workflow Continuation Bug** ✅ **FIXED**

**Status**: ✅ **Already implemented in code**

**Evidence** ([src/services/workflow_orchestrator.py](src/services/workflow_orchestrator.py:118)):
```python
async def _get_or_create_workflow(self, ...):
    """Create or continue existing workflow execution record."""

    # ✅ Checks for existing workflows
    result = await session.execute(
        select(WorkflowExecution)
        .where(WorkflowExecution.user_id == user_id)
        .where(WorkflowExecution.certification_profile_id == certification_profile_id)
        .where(WorkflowExecution.execution_status != WorkflowStatus.COMPLETED)
        .where(WorkflowExecution.execution_status != WorkflowStatus.ERROR)
    )
    existing_workflows = result.scalars().all()

    # ✅ Handles multiple workflows (auto-completes duplicates)
    if len(existing_workflows) > 1:
        for old_workflow in existing_workflows[1:]:
            old_workflow.execution_status = WorkflowStatus.COMPLETED

    # ✅ Returns existing workflow if found
    if existing_workflow:
        self.logger.info("Continuing existing workflow execution")
        return existing_workflow

    # ✅ Only creates new if none exists
    workflow = WorkflowExecution(...)
    self.logger.info("Created new workflow execution")
```

**Verdict**: ✅ **No action needed in Sprint 0**

---

### **Bug 2: DateTime Serialization** ✅ **NOT FOUND (Likely Fixed)**

**Status**: ✅ **No evidence of DateTime serialization issues**

**Investigation**:
- Searched [form_response_processor.py](src/services/form_response_processor.py) - no datetime serialization code found
- Searched [response_ingestion_service.py](src/services/response_ingestion_service.py:1) - uses standard `datetime` imports
- All datetime handling uses Python's `datetime.datetime` (native serialization)
- No custom serializers or fromisoformat() calls that could fail

**Evidence**:
```python
# response_ingestion_service.py lines 1-10
from datetime import datetime, timedelta
# Standard Python datetime - no custom serialization
```

**Verdict**: ✅ **No action needed in Sprint 0** (already fixed or never existed)

---

### **Bug 3: Gap Analysis API Parsing Error** 🟡 **NEEDS INVESTIGATION**

**Status**: 🟡 **Potential issue exists - needs validation**

**Evidence Found**:
- Grep found 3 files with "parse server response" references:
  1. [response_ingestion_service.py](src/services/response_ingestion_service.py)
  2. [form_template_manager.py](src/services/form_template_manager.py)
  3. [llm_service.py](src/services/llm_service.py)

**No explicit error handling for "Failed to parse server response" found in code**

**Possible Causes**:
1. **Frontend UI issue**: Dashboard making malformed API requests
2. **JSON response format mismatch**: Gap analysis returning unexpected structure
3. **HTTP status code handling**: 500 errors being parsed as JSON
4. **CORS or network errors**: Intercepted before reaching API handler

**Required Investigation**:
- [ ] Check frontend [Gap Analysis Dashboard] code for API call format
- [ ] Review API endpoint `/api/v1/workflows/{id}/gap-analysis` response schema
- [ ] Add explicit error handling in API response serialization
- [ ] Add logging for all Gap Analysis API calls to identify failure point

**Verdict**: 🟡 **Add to Sprint 0** - Requires investigation + potential fix

---

## 3. Google Sheet Linkage & Discovery

### **Current State**: ❌ No automatic Sheet creation

**Clarification from User**:
> "Currently, a linked Google Sheet is NOT created → Explicitly create the Sheet via Sheets API and Link it to the Form via Drive API"

### **Required Implementation**

#### **Step 1: Create Google Sheet via Sheets API**
```python
# src/services/google_sheets_service.py
async def create_linked_sheet(self, form_id: str, certification_name: str) -> Dict[str, str]:
    """Create a Google Sheet linked to the Form."""

    # 1. Create new spreadsheet
    sheet_metadata = {
        "properties": {
            "title": f"{certification_name} Assessment Results"
        }
    }

    sheet = self.sheets_service.spreadsheets().create(
        body=sheet_metadata
    ).execute()

    sheet_id = sheet["spreadsheetId"]

    # 2. Link Sheet to Form (via Drive API)
    await self._link_sheet_to_form(sheet_id, form_id)

    return {
        "sheet_id": sheet_id,
        "sheet_url": sheet["spreadsheetUrl"]
    }
```

#### **Step 2: Link Sheet to Form via Drive API**
```python
async def _link_sheet_to_form(self, sheet_id: str, form_id: str):
    """Link Sheet to Form by placing in same folder + metadata."""

    # Option 1: Store relationship in database
    # Store form_id → sheet_id mapping in workflow.google_sheet_id

    # Option 2: Use Drive API to get Form's parent folder
    drive_service = self.google_services.get_drive_client()

    form_metadata = drive_service.files().get(
        fileId=form_id,
        fields="parents"
    ).execute()

    parent_folder = form_metadata.get("parents", [])[0]

    # Move sheet to same folder as form
    drive_service.files().update(
        fileId=sheet_id,
        addParents=parent_folder,
        removeParents="root",
        fields="id, parents"
    ).execute()
```

#### **Step 3: Retrieve Sheet ID from Form**
**Suggested Method**: Store in database during creation

```python
# In workflow_orchestrator.py
async def _create_form_and_sheet(self, workflow, assessment_data):
    # Create Form
    form_result = await self.google_forms_service.create_assessment_form(...)
    form_id = form_result["form_id"]

    # Create linked Sheet
    sheet_result = await self.google_sheets_service.create_linked_sheet(
        form_id=form_id,
        certification_name=assessment_data["metadata"]["certification_name"]
    )
    sheet_id = sheet_result["sheet_id"]

    # Store in workflow
    workflow.google_form_id = form_id
    workflow.google_sheet_id = sheet_id  # ✅ Store for future reference

    await session.commit()
```

**Alternative Method**: Query Drive API to find Sheet by form parent folder
```python
async def find_sheet_for_form(self, form_id: str) -> Optional[str]:
    """Find Sheet ID by searching Form's parent folder."""
    drive_service = self.google_services.get_drive_client()

    # Get Form's folder
    form_metadata = drive_service.files().get(
        fileId=form_id,
        fields="parents"
    ).execute()
    parent_folder = form_metadata.get("parents", [])[0]

    # Search for Sheet in same folder
    query = f"'{parent_folder}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
    results = drive_service.files().list(q=query).execute()

    sheets = results.get("files", [])
    return sheets[0]["id"] if sheets else None
```

**Recommended**: **Database storage** (faster, more reliable)

---

## 4. Gap Analysis Dashboard Enhancements

### **Required Features**

#### **Feature 1: Text Summary of Results** ✅
```typescript
// Gap Analysis Dashboard Component
<div className="results-summary">
  <h3>Assessment Results Summary</h3>
  <p>
    You scored {overallScore}% on this assessment. Based on your results,
    we identified {gapCount} areas for improvement across {domainCount}
    certification domains. Your strongest performance was in {strongestDomain},
    while {weakestDomain} requires additional study.
  </p>

  <div className="key-insights">
    <h4>Key Insights:</h4>
    <ul>
      {insights.map(insight => (
        <li key={insight.id}>{insight.text}</li>
      ))}
    </ul>
  </div>
</div>
```

#### **Feature 2: Interactive Chart Tooltips** ✅
```typescript
// Chart with tooltips
<ResponsiveBar
  data={gapData}
  tooltip={({ id, value, data }) => (
    <div className="custom-tooltip">
      <strong>{id}</strong>
      <p>Gap Severity: {value}</p>
      <p className="tooltip-explanation">
        {getTooltipExplanation(id, value)}
      </p>
    </div>
  )}
/>

function getTooltipExplanation(domain: string, severity: number): string {
  if (severity > 7) {
    return `Critical gap - Focus on ${domain} immediately. This area requires significant study.`;
  } else if (severity > 4) {
    return `Moderate gap - Review ${domain} concepts. You have partial understanding but need reinforcement.`;
  } else {
    return `Minor gap - Quick review of ${domain} recommended. You're mostly proficient.`;
  }
}
```

#### **Feature 3: Side Panel with Chart Legend** ✅
```typescript
<div className="dashboard-layout">
  <div className="charts-container">
    {/* Charts */}
  </div>

  <aside className="interpretation-panel">
    <h3>How to Read These Charts</h3>

    <div className="legend-item">
      <h4>🔴 Gap Severity (Red Bars)</h4>
      <p>
        Indicates how significant the knowledge gap is. Higher bars mean
        you need more study time in that area. Scores above 7/10 require
        immediate attention.
      </p>
    </div>

    <div className="legend-item">
      <h4>📊 Domain Distribution (Pie Chart)</h4>
      <p>
        Shows which certification domains had the most incorrect answers.
        Larger slices indicate areas where you should focus your study efforts.
      </p>
    </div>

    <div className="legend-item">
      <h4>📈 Performance Trend (Line Graph)</h4>
      <p>
        Tracks your progress over time. Upward trends show improvement,
        while flat or declining trends suggest you need to revisit those topics.
      </p>
    </div>
  </aside>
</div>
```

#### **Feature 4: Tabbed Display with Content Outline & Course List** ✅

**Tab 1: Content Outline**
```typescript
<Tabs defaultValue="outline">
  <TabsList>
    <TabsTrigger value="outline">Content Outline</TabsTrigger>
    <TabsTrigger value="courses">Recommended Courses</TabsTrigger>
  </TabsList>

  <TabsContent value="outline">
    <h3>Missing Skills - Detailed Content Map</h3>
    {skillGaps.map(gap => (
      <div key={gap.skillId} className="outline-section">
        <h4>{gap.domain} → {gap.skillName}</h4>
        <div className="content-mapping">
          <p><strong>Exam Guide Reference:</strong> {gap.examGuideSection}</p>
          <p><strong>Content Coverage:</strong></p>
          <ul>
            {gap.contentOutline.map(item => (
              <li key={item.id}>
                {item.topic} - <em>{item.source}</em>
              </li>
            ))}
          </ul>
        </div>
      </div>
    ))}
  </TabsContent>

  <TabsContent value="courses">
    <h3>Recommended Courses to Generate</h3>
    <table className="courses-table">
      <thead>
        <tr>
          <th>Course Title</th>
          <th>Mapped Domain</th>
          <th>Skills Covered</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {recommendedCourses.map(course => (
          <tr key={course.id}>
            <td>{course.title}</td>
            <td>{course.examDomain}</td>
            <td>
              <ul className="skills-list">
                {course.skillsCovered.map(skill => (
                  <li key={skill}>{skill}</li>
                ))}
              </ul>
            </td>
            <td>
              {course.status === 'pending' && (
                <Button onClick={() => generateCourse(course.id)}>
                  Generate Course
                </Button>
              )}
              {course.status === 'generating' && (
                <div className="timer-tracker">
                  <Spinner />
                  <span>Generating... {course.elapsed}s</span>
                </div>
              )}
              {course.status === 'completed' && (
                <div className="course-actions">
                  <Button onClick={() => launchCourse(course.videoUrl)}>
                    Launch Course
                  </Button>
                  <Button variant="outline" onClick={() => downloadCourse(course.downloadUrl)}>
                    Download
                  </Button>
                </div>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </TabsContent>
</Tabs>
```

**Course Generation Flow**:
```typescript
async function generateCourse(courseId: string) {
  // Update UI to show "Generating"
  updateCourseStatus(courseId, 'generating');

  // Start timer tracker
  const startTime = Date.now();
  const timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    updateCourseTimer(courseId, elapsed);
  }, 1000);

  try {
    // Call PresGen-Avatar API
    const response = await fetch('/api/v1/avatar/generate-course', {
      method: 'POST',
      body: JSON.stringify({
        course_id: courseId,
        mode: 'presentation-only'
      })
    });

    const result = await response.json();

    // Stop timer
    clearInterval(timerInterval);

    // Update to "Completed"
    updateCourseStatus(courseId, 'completed', {
      videoUrl: result.video_url,
      downloadUrl: result.download_url,
      duration: result.duration_seconds
    });

    // Add to Google Sheet
    await addCourseToSheet(courseId, result);

  } catch (error) {
    clearInterval(timerInterval);
    updateCourseStatus(courseId, 'failed');
    showError('Course generation failed. Please try again.');
  }
}

function launchCourse(videoUrl: string) {
  // Use existing Presgen-avatar video player
  // (Import video player component from presgen-avatar project)
  openVideoPlayer({
    url: videoUrl,
    autoplay: true,
    controls: true
  });
}

function downloadCourse(downloadUrl: string) {
  // Trigger download
  window.open(downloadUrl, '_blank');
}
```

---

## 5. Updated Workflow Requirements

### **Assessment Creation Flow (AI-Powered)**

```
1. User creates Assessment Workflow in UI
   ↓
2. User uploads Certification Resources (exam guide, transcript)
   ↓
3. User clicks "Generate Assessment" button
   ↓
4. Backend triggers AIQuestionGenerator
   ├─ Retrieves uploaded resources from knowledge base
   ├─ Uses certification profile assessment prompt
   ├─ Generates questions with RAG + LLM
   ├─ Maps each question to exam guide skills
   └─ Validates quality (min 8.0/10 score)
   ↓
5. Questions formatted via AssessmentFormsMapper
   ↓
6. Google Form created with questions
   ↓
7. Google Sheet created and linked to Form
   ↓
8. Workflow status: "Awaiting Completion"
   ↓
9. Learner receives Form link and completes assessment
   ↓
10. User clicks "Trigger Response Collection" in UI
    ↓
11. Backend ingests responses, performs Gap Analysis
    ↓
12. Gap Analysis Dashboard displays:
    ├─ Text summary of results
    ├─ Charts with tooltips
    ├─ Side panel with interpretation guide
    ├─ Tab 1: Content Outline (skills mapped to resources)
    └─ Tab 2: Recommended Courses (with Generate buttons)
    ↓
13. User clicks "Generate Course" for each skill gap
    ├─ Timer tracker shows progress
    ├─ PresGen-Avatar generates narrated presentation
    └─ On completion: Launch + Download buttons appear
    ↓
14. Course links added to Google Sheet
    ↓
15. Workflow status: "Completed"
```

---

## 6. Outstanding Questions for Next Phase

### **Question 1: AI Question Generation Trigger**
**Clarified**: ✅ User-triggered from UI workflow button (not automatic)

### **Question 2: Google Sheet Discovery**
**Clarified**: ✅ Create via Sheets API + store in database (not auto-created)

### **Question 3: Resource Recommendation Timing**
**Clarified**: ✅ After Gap Analysis, before generation (user selects which courses to generate)

### **Question 4: Chart Interpretation**
**Clarified**: ✅ Text summary + tooltips + side panel + tabbed display

### **Question 5: Bug Fixes**
**Clarified**:
- ✅ Workflow continuation: Already fixed
- ✅ DateTime serialization: Already fixed or non-existent
- 🟡 Gap Analysis API parsing: Needs investigation in Sprint 0

---

## Next Steps

1. ✅ Create detailed comparison of AssessmentFormsMapper vs AIQuestionGenerator
2. ✅ Validate bug fix status for Sprint 0
3. ⏳ Create updated project plan incorporating all clarifications
4. ⏳ Define Sprint 0 tasks with bug investigation
5. ⏳ Design Google Sheet creation + linkage implementation
6. ⏳ Design Gap Analysis Dashboard UI components
