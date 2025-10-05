# Gap Analysis ➜ Google Sheets ➜ Avatar Narrated Presentations

_Last updated: 2025-09-29_

## 0. Overview
- **Scope:** Fully automated workflow from assessment request to avatar-narrated presentation using the Google Form–linked Sheet (no prompt separation changes in this phase; that work remains deferred per roadmap).
- **Pipeline:** Assessment Request → Google Form generation → Gap Analysis enrichment → Populate 4 additional tabs on the Form-linked Google Sheet → PresGen-Core presentation generation → PresGen-Avatar narration.
- **Duration:** 10 weeks total (Sprint 0 foundation + Sprints 1–5 execution).
- **Stakeholders:** Backend platform, frontend UX, DevOps, QA, Instructional design.

### Sprint Timeline
| Sprint | Weeks | Focus | Key Deliverables |
| --- | --- | --- | --- |
| 0 | Week 0 | Contracts & flags | Signed-off API schema, config templates, feature flags wired |
| 1 | Weeks 1–2 | Gap analysis enrichment | Learning objectives service, augmented API payload |
| 2 | Weeks 3–4 | Sheet population | Form-linked Sheet tabs, rate limiter toggle, dashboard updates |
| 3 | Weeks 5–6 | Content orchestration & PresGen-Core | Slide deck generator, queue + Drive integration |
| 4 | Weeks 7–8 | Avatar narration | Script pipeline, PresGen-Avatar integration, presentation tab updates |
| 5 | Weeks 9–10 | Hardening & pilot | Automated QA, observability dashboards, pilot sign-off |

### Dependencies & Assumptions
- Prompt individuation will be tackled later; current work must avoid altering existing prompt storage contracts.
- Google APIs (Forms, Sheets, Drive) credentials are available and authorized prior to Sprint 2.
- PresGen-Core and PresGen-Avatar services expose stable health endpoints and queue-friendly APIs.
- Feature flags default **off** in production until QA sign-off.

---

## Sprint 0 (Week 0): Service Contracts, Configuration Templates, Feature Flags

### Objectives
1. Lock down service contracts for workflow, gap analysis, and sheet orchestration endpoints.
2. Produce configuration templates for all new environment variables and secrets.
3. Implement feature flags to gate Sheets population, PresGen-Core submissions, and avatar narration.

### Key Activities & Artifacts

#### 0.1 Service Contract Finalization
- Publish OpenAPI patch covering enriched `GET /api/v1/workflows/{id}/gap-analysis` response.
- Generate TypeScript/Zod definitions for presgen-ui clients and commit to `presgen-ui/src/lib/api/types/`.
- Document backward compatibility strategy: older clients continue to receive `gap_summary` field (deprecated after Sprint 4).

```json
// excerpt: openapi_overrides/gap_analysis.json
{
  "WorkflowGapAnalysisResponse": {
    "type": "object",
    "required": ["workflow_id", "objectives", "skill_matrix", "recommendations"],
    "properties": {
      "workflow_id": { "type": "string", "format": "uuid" },
      "objectives": {
        "type": "array",
        "items": { "$ref": "#/components/schemas/LearningObjective" }
      },
      "skill_matrix": {
        "type": "array",
        "items": { "$ref": "#/components/schemas/SkillGap" }
      },
      "sheet_metadata": {
        "type": "object",
        "properties": {
          "form_sheet_id": { "type": "string" },
          "tab_ranges": { "type": "object", "additionalProperties": { "type": "string" } }
        }
      }
    }
  }
}
```

#### 0.2 Configuration Templates
- Extend `.env.example` with Google API scopes, Drive folder root, PresGen-Core/Avatar URLs, flag toggles.

```dotenv
# Google API
GOOGLE_APPLICATION_CREDENTIALS=./config/google-sa.json
GOOGLE_FORMS_API_BASE=https://forms.googleapis.com/v1
GOOGLE_SHEETS_API_BASE=https://sheets.googleapis.com/v4
GOOGLE_DRIVE_ROOT_FOLDER_ID=

# Downstream integrations
PRESGEN_CORE_BASE_URL=https://presgen-core.staging.internal
PRESGEN_AVATAR_BASE_URL=https://presgen-avatar.staging.internal

# Feature flags (boolean string)
ENABLE_SHEETS_TAB_POPULATION=false
ENABLE_PRESGEN_CORE_SUBMISSION=false
ENABLE_AVATAR_NARRATION=false
ENABLE_GOOGLE_RATE_LIMITER=false  # remains false in dev/local
```

- Provide Terraform/Helm variable defaults for production secrets rotation and reference them in infrastructure repository.

#### 0.3 Feature Flags Wiring
- Add `FeatureToggle` utility reading env vars and expose via dependency injection.

```python
# src/common/feature_flags.py
from functools import cached_property
from pydantic import BaseSettings

class FeatureFlagSettings(BaseSettings):
    enable_sheets_tab_population: bool = False
    enable_presgen_core_submission: bool = False
    enable_avatar_narration: bool = False
    enable_google_rate_limiter: bool = False

flags = FeatureFlagSettings()

# usage
if flags.enable_sheets_tab_population:
    await sheet_builder.populate_tabs(...)
```

### Exit Criteria
- API contracts reviewed and signed off by backend + frontend leads.
- Config templates merged with documentation in `README.md`.
- Feature flags available in API and UI layers with logging when toggled.

---

## Sprint 1 (Weeks 1–2): Gap Analysis Enrichment & Learning Objectives

### Objectives
1. Translate raw assessment results into structured learning objectives aligned with certification taxonomy.
2. Enrich gap analysis payload with metadata required for Sheets, PresGen-Core, and Avatar stages.
3. Maintain existing UI responses while adding new fields (deprecated ones remain until Sprint 5).

### Detailed Tasks
- **Learning Objective Builder:**
  - Inputs: incorrect answers, confidence scores, domain weights, learner profile.
  - Outputs: SMART objective records with severity, effort estimate, recommended timeline.
  - Map each objective to RAG resources (exam guide sections, transcripts).

```python
# src/services/gap_analysis/objectives.py
@dataclass
class LearningObjective:
    skill_id: str
    objective: str
    severity: int
    effort_hours: float
    exam_weight: float
    timeline_days: int
    resources: list[str]

class LearningObjectiveBuilder:
    def build(self, gaps: list[SkillGap], persona: Persona) -> list[LearningObjective]:
        objectives = []
        for gap in gaps:
            severity = self._calc_severity(gap)
            effort = self._estimate_effort_hours(gap, persona)
            timeline = max(3, int(effort / persona.hours_per_day))
            objectives.append(
                LearningObjective(
                    skill_id=gap.skill_id,
                    objective=f"Master {gap.skill_name} at {gap.target_level} proficiency",
                    severity=severity,
                    effort_hours=effort,
                    exam_weight=gap.exam_weight,
                    timeline_days=timeline,
                    resources=self._recommend_resources(gap)
                )
            )
        return sorted(objectives, key=lambda obj: (-obj.severity, -obj.exam_weight))
```

- **Priority Matrix:** Combine severity, exam weight, learner confidence/accuracy delta, persona goals to create ranking used later by Sheets & Outline.
- **Gap Analysis API Update:** Add `objectives`, `priority_matrix`, `sheet_metadata` placeholders to response. Maintain `legacy_summary` for existing dashboards.

```python
# src/service/api/v1/endpoints/workflows.py (excerpt)
response = GapAnalysisResponse(
    workflow_id=workflow.id,
    objectives=objective_builder.build(gaps, persona),
    priority_matrix=priority_service.calculate(gaps, persona),
    sheet_metadata=SheetMetadata(
        form_sheet_id=workflow.google_sheet_id,
        tab_ranges={}
    ),
    legacy_summary=existing_summary
)
```

- **Testing:**
  - Unit tests for severity/effort calculations and resource linking.
  - Integration tests verifying API compatibility with old clients.
  - Scenario fixtures for different certifications (AWS SAA, AWS MLA).

### Deliverables
- Updated `GapAnalysisResponse` schema and data classes.
- Learning objective service with 90%+ coverage.
- Documentation in `PHASE_4_DETAILED_PROJECT_PLAN.md` appendices.

### Acceptance Criteria
- For a sample workflow, objectives list covers all incorrect domains with severity scoring matching spec.
- API latency remains <300 ms for gap analysis endpoint.
- Legacy UI continues to render using `legacy_summary` without changes.

---

## Sprint 2 (Weeks 3–4): Google Sheets Tab Population (Form-Linked Sheet)

### Objectives
1. Populate 4 additional tabs (`Answers`, `Gap Analysis`, `Outline`, `Presentation`) on the **existing** Google Sheet linked to the assessment’s Google Form.
2. Build a robust sheet builder service with idempotent tab creation, formatting, and data population.
3. Introduce environment-controlled Google API rate limiter (disabled in dev/local).
4. Preserve current dashboard “Export to Sheets” feature—continue generating a standalone summary sheet for manual sharing.

### Architecture Diagram (Textual)
```
Gap Analysis Service → Sheet Builder → Google Sheets API
                    ↘           ↘
                     Workflow State  Dashboard Export (existing new sheet)
```

### Detailed Tasks

#### 2.1 Sheet Builder Service
- Fetch form-linked Sheet ID from workflow record.
- Ensure sheet tabs exist (create if missing) and cache tab IDs.
- Write data using batchUpdate with value ranges and formatting.
- Update workflow state with `tab_ranges` for later updates (presentations, avatar URLs).

```python
# src/integrations/google/sheet_builder.py
class SheetBuilder:
    def __init__(self, sheets_client: SheetsClient, flags: FeatureFlagSettings):
        self.sheets = sheets_client
        self.flags = flags

    async def populate_tabs(self, workflow: Workflow, payload: GapAnalysisPayload) -> SheetMetadata:
        if not self.flags.enable_sheets_tab_population:
            logger.info("Sheet population disabled via flag")
            return SheetMetadata(form_sheet_id=workflow.google_sheet_id, tab_ranges={})

        sheet_id = workflow.google_sheet_id
        await self._ensure_tabs(sheet_id)
        await self._write_answers_tab(sheet_id, payload.answers)
        await self._write_gap_tab(sheet_id, payload.skill_matrix)
        await self._write_outline_tab(sheet_id, payload.objectives)
        metadata = await self._write_presentation_tab(sheet_id, payload.presentation_placeholders)

        return SheetMetadata(form_sheet_id=sheet_id, tab_ranges=metadata)

    async def _ensure_tabs(self, sheet_id: str) -> None:
        existing_tabs = await self.sheets.list_tabs(sheet_id)
        required = {
            "Answers": self._build_answers_template,
            "Gap Analysis": self._build_gap_template,
            "Outline": self._build_outline_template,
            "Presentation": self._build_presentation_template,
        }
        for title, template in required.items():
            if title not in existing_tabs:
                await self.sheets.add_tab(sheet_id, title)
                await template(sheet_id, title)
```

- Formatting templates include conditional color scales for severity, charts for domain scores, and hyperlink columns for Drive assets.

#### 2.2 Rate Limiter Toggle
- Wrap Google client calls with limiter when `ENABLE_GOOGLE_RATE_LIMITER=true` (staging/prod).

```python
# src/integrations/google/clients.py
class SheetsClient:
    def __init__(self, session: AuthorizedSession, flags: FeatureFlagSettings):
        self.session = session
        self.flags = flags
        self._limiter = AsyncRateLimiter(rate=8/second) if flags.enable_google_rate_limiter else None

    async def _request(self, method: str, url: str, **kwargs):
        if self._limiter:
            async with self._limiter:
                return await self.session.request(method, url, **kwargs)
        return await self.session.request(method, url, **kwargs)
```

#### 2.3 Dashboard Export Behavior (Unchanged)
- Maintain existing “Export to Sheets” button that creates a standalone summary sheet.
- Update UX copy: “Automated pipeline writes to the Google Form’s linked Sheet; this export generates an additional shareable copy.”

#### 2.4 Frontend Updates
- Display tab population status in workflow timeline (`Sheet tabs synced` badge).
- Surface links to the four tabs inside workflow details drawer.

### Testing
- Integration tests hitting Google Sheets sandbox verifying data placement and formatting.
- Failure simulations for missing sheet ID, permission errors, API quota exceeded.
- Playwright tests verifying UI shows sheet links when flag enabled.

### Acceptance Criteria
- For QA workflow, 4 tabs created/updated on Form-linked Sheet within 60 seconds.
- Conditional formatting and charts render correctly (manual QA script).
- Rate limiter toggle verified: disabled in dev (no throttling), enabled in staging (observed via logs).
- Dashboard export still generates separate summary sheet.

---

## Sprint 3 (Weeks 5–6): Content Orchestration & PresGen-Core Integration

### Objectives
1. Transform enriched gap analysis into structured slide outlines with narrative points.
2. Integrate with PresGen-Core using a resilient job queue (async submission, retries, circuit breaker).
3. Organize generated assets in Drive and update Presentation tab placeholders with real links and job metadata.

### Use Cases & Components
- **Content Orchestration Service:** Derives slide sequences from learning objectives, ensuring consistent pedagogy.
- **Template Catalog:** Chooses presentation template based on certification, learner severity, desired slide count.
- **Job Queue:** Buffers PresGen-Core requests to prevent API overload; supports manual retry/resume.
- **Drive Organizer:** Places markdown/json assets into learner-specific folders for later avatar consumption.

### Implementation Details

```python
# src/services/content_orchestration/service.py
class ContentOrchestrationService:
    def __init__(self, knowledge_service, template_selector):
        self.knowledge_service = knowledge_service
        self.template_selector = template_selector

    async def build_slide_deck(self, objectives: list[LearningObjective], persona: Persona) -> SlideDeck:
        template = self.template_selector.pick(persona.certification_id, len(objectives))
        slides = []
        for objective in objectives:
            resources = await self.knowledge_service.fetch_resources(objective.skill_id)
            slides.append(Slide(
                title=f"{objective.skill_name} Mastery",
                bullets=[r.summary for r in resources],
                references=[r.url for r in resources],
                speaking_points=self._build_speaking_points(objective, resources)
            ))
        return SlideDeck(template_id=template.id, slides=slides)
```

```python
# src/integrations/presgen_core/queue.py
class PresentationJobQueue:
    def __init__(self, broker: Broker, flags: FeatureFlagSettings):
        self.broker = broker
        self.flags = flags
        self.circuit_breaker = CircuitBreaker(max_failures=3, reset_timeout=300)

    async def submit(self, deck: SlideDeck, workflow: Workflow):
        if not self.flags.enable_presgen_core_submission:
            logger.info("PresGen-Core submission disabled via flag")
            return None
        job = PresentationJob(workflow_id=workflow.id, payload=deck)
        await self.broker.enqueue(job)
        return job.id
```

- **Worker Process:** Pulls jobs, calls PresGen-Core API with retries/backoff, updates job status, writes output to Drive.

```python
async def process_job(job: PresentationJob):
    try:
        response = await presgen_core_client.create_presentation(job.payload)
        drive_path = await drive_manager.store_presentation(response.files, job.workflow_id)
        await sheet_builder.update_presentation_tab(job.workflow_id, response.summary, drive_path)
        await job_store.mark_complete(job.id, drive_path)
    except Exception as exc:
        await job_store.mark_failed(job.id, str(exc))
        raise
```

### Testing
- Unit tests for slide generation and template selection accuracy.
- Integration tests using PresGen-Core sandbox (mock server verifying payloads, rate-limits, circuit breaker transitions).
- Load tests for queue throughput (target: 30 jobs/hr sustained).

### Acceptance Criteria
- Slide deck includes executive summary, gap dives, remediation plan, follow-up steps.
- Queue recovers from simulated PresGen-Core outage (circuit breaker opens/closes as expected).
- Presentation tab updated with links, job status, template metadata.
- Drive structure matches `Certifications/{Certification}/{Learner}/Presentations/` hierarchy.

---

## Sprint 4 (Weeks 7–8): Avatar Narration Integration

### Objectives
1. Convert generated slide content into narration scripts and submit to PresGen-Avatar.
2. Poll for avatar video completion, capture metadata, and update Presentation tab + workflow state.
3. Provide manual retry/fallback controls and quality review hooks.

### Detailed Steps

#### 4.1 Script Generation
- Derive narration text from slide speaking points with pacing cues (approx 120 words/minute).

```python
def build_script(slide: Slide) -> str:
    lines = [f"Slide Title: {slide.title}"]
    for bullet in slide.bullets:
        lines.append(f"Discuss: {bullet}")
    lines.append("Prompt learner to review references provided.")
    return "\n".join(lines)
```

#### 4.2 PresGen-Avatar Client Enhancements

```python
# src/integrations/presgen_avatar/client.py
class PresGenAvatarClient:
    async def submit_narration(self, script: str, deck: SlideDeck, persona: Persona) -> AvatarJob:
        if not flags.enable_avatar_narration:
            logger.info("Avatar narration disabled via flag")
            return AvatarJob(skipped=True)
        payload = {
            "script": script,
            "voice_profile": persona.voice_style,
            "presentation_assets": deck.export_for_avatar()
        }
        response = await self._request("POST", "/api/v1/avatar/videos", json=payload)
        return AvatarJob(id=response["job_id"], status=response["status"])

    async def poll(self, job_id: str) -> AvatarResult:
        while True:
            result = await self._request("GET", f"/api/v1/avatar/videos/{job_id}")
            if result["status"] in {"completed", "failed"}:
                return AvatarResult(**result)
            await asyncio.sleep(30)
```

#### 4.3 Presentation Tab Update
- Rewrite `Presentation` tab rows with columns `[Topic, Slide Deck Link, Avatar Video Link, Duration, Status, QA Reviewer]` once narration completes.
- Add QA checklist column for human reviewers.

#### 4.4 Fallbacks & Manual Controls
- API endpoint `/api/v1/workflows/{id}/retry-avatar` allowing operators to re-run failed narration jobs.
- Log structured events: submission, polling, completion, QA approval.

### Testing
- Integration tests using PresGen-Avatar staging (mocked long-running jobs, failure cases).
- Manual QA script verifying video plays, timing matches slide count, voice style appropriate.
- Monitoring alerts for jobs exceeding 20 minutes.

### Acceptance Criteria
- Successful workflows produce at least one avatar video link per presentation, stored in Drive and Presentation tab.
- QA reviewers can mark approval directly in Sheet or via UI.
- Retry endpoint tested with simulated failures, verifying idempotent behavior.

---

## Sprint 5 (Weeks 9–10): Hardening, QA, Deployment Prep

### Focus Areas
- **Automated Testing:** Convert manual TDD scripts (`PHASE_4_SPRINT_1_TDD_MANUAL_TESTING.md`) into pytest suites and Playwright E2E covering full pipeline.
- **Observability:** Extend enhanced logging to cover Sheets, PresGen-Core, Avatar stages; add metrics (job throughput, failure rates, sheet latency) to Grafana.
- **Security & Compliance:** Review Google Drive permissions, rotate service-account keys, run accessibility/bias checks on content and narration.
- **Pilot Launch:** Run end-to-end pilot with real certification content, gather SME feedback, finalize rollback plan.

### Deliverables Checklist
- [ ] Automated regression suite green in CI.
- [ ] Dashboard panels for pipeline stages with alerting thresholds.
- [ ] Runbook updates for operators (Sheets failures, job retries, manual override).
- [ ] Pilot report + sign-off from instructional team.

---

## Risks & Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Google API quota exhaustion | Sheet writes fail | Implement toggleable rate limiter, exponential backoff, preflight quota checks |
| PresGen-Core instability | Presentation backlog | Circuit breaker + queue retries; manual resume endpoints |
| Avatar narration quality issues | Learner trust | QA checklist, ability to re-run with different voice profile |
| Sheet tab collision | Data corruption | Idempotent tab creation, naming convention enforcement |
| Configuration drift | Deployment failures | Shared config templates and automated validation in CI |

---

## Acceptance Summary
- **Sprint 0:** Contracts & flags approved, configs documented.
- **Sprint 1:** Gap analysis API returns objectives + priority data without breaking existing clients.
- **Sprint 2:** Form-linked Sheet enriched with 4 tabs, rate limiter toggle honored, manual export untouched.
- **Sprint 3:** Slide decks generated, queued, stored in Drive, Presentation tab updated.
- **Sprint 4:** Avatar narration produces accessible videos, Presentation tab finalized, retries available.
- **Sprint 5:** Monitoring, QA, and pilot sign-off complete prior to flag enablement in production.

---

## Next Steps After Completion
1. Revisit prompt individuation plan to split knowledge-base vs profile prompts safely.
2. Extend Presentation tab to include learner feedback metrics and re-assessment scheduling.
3. Evaluate dynamic rate limiting and autoscaling for PresGen-Core/Avatar workers.
