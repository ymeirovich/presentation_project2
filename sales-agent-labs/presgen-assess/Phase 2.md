# Phase 2 – Assessment & Gap Engines (Weeks 4-7)

## Objectives
- Deliver an LLM-driven assessment generator that pulls contextual knowledge from the Phase 1 vector store and produces Bloom-aligned, psychometrically valid question sets (`architecture.md:55`, `presgen_assessment_prd.md:134`).
- Implement the multi-dimensional gap analysis engine that transforms assessment results into remediation insights, covering knowledge, skills, application, confidence, and depth dimensions (`architecture.md:151`, `presgen_assessment_prd.md:166`).
- Expose FastAPI endpoints, async workers, and data contracts powering the assessment lifecycle, ensuring tests, telemetry, and documentation keep pace with new capabilities (`README.md:157`, `specification.md:53`).

## Scope
- Services within `src/assessment/` (generator, analyzer, validator) and supporting models in `src/models/`.
- Gap analysis computation pipeline, remediation planning logic, and data outputs to Google Sheets-compatible structures.
- HTTP API layer additions (assessment request, status tracking, completion processing) and background processing hooks.
- Test suites spanning unit, contract, integration, performance, and security for new services.
- Observability enhancements capturing LLM prompts, scoring metrics, and gap analysis performance.

## Out of Scope
- Workflow orchestration state machine and Google Workspace integrations (Phase 3).
- Frontend dashboards or learner-facing presentation/avatars (Phase 4).
- Knowledge base ingestion changes beyond bug fixes or minor tuning (Phase 1).

## Deliverables
1. **Assessment Generator Service**: RAG retrieval, prompt templating, question/distractor generation, and validation pipeline (`src/assessment/generator.py`, `specification.md:146`).
2. **Gap Analysis Engine**: Multi-dimensional scoring, skill mapping, remediation plan synthesis, and export adapters (`src/assessment/analyzer.py`, `presgen_assessment_prd.md:168`).
3. **Validation & QA Module**: Automated checks on question quality, difficulty mix, bias detection, and rubric generation (`src/assessment/validator.py`, `architecture.md:133`).
4. **API & Background Workers**: FastAPI routes plus async tasks for assessment creation, completion processing, and report retrieval (`README.md:157`).
5. **Testing & Observability**: Comprehensive pytest suites, load tests (<3-minute generation), structured logging, metrics, and alert definitions (`presgen_assessment_prd.md:158`).

## Timeline & Milestones
- **Week 4 – Prototyping & Foundations**
  - Finalize RAG prompt templates and question schema definitions.
  - Implement minimal viable generator using seeded certification profiles for AWS/Azure domains.
  - Draft gap analysis framework with placeholder scoring to validate data pathways.
- **Week 5 – Engine Completion**
  - Expand generator for Bloom taxonomy coverage, distractor generation, and rubric creation.
  - Complete gap analysis algorithms, severity scoring, and personalized remediation plan outputs.
  - Integrate validator module to enforce pedagogical and psychometric checks.
- **Week 6 – API & Integration**
  - Implement FastAPI routes, background workers, and persistence for assessment sessions.
  - Connect gap analysis outputs to structured data exports (Sheets-ready JSON/CSV formats).
  - Harden error handling, retries, and logging for LLM + vector store interactions.
- **Week 7 – Testing & Performance**
  - Build contract/integration/performance/security test suites and automate in CI.
  - Conduct load/performance runs to confirm <3-minute assessment generation and <1-minute gap processing.
  - Finalize documentation, run dry-run workflows, and triage remaining defects before handover to Phase 3.

## Detailed Workstreams
### 1. Assessment Generator
- [ ] **Schema Definition**: Finalize Pydantic models for questions, options, and rubrics in `src/models/assessment.py`.
- [ ] **RAG Wrapper**: Implement a `retrieve_context` function in `src/assessment/generator.py` that queries ChromaDB.
- [ ] **Prompt Engineering**: Develop and test prompt templates in `config/prompts.yaml` for different question types.
- [ ] **Generation Logic**: Build the core `generate_questions` method using the RAG wrapper and prompt templates.
- [ ] **Distractor Service**: Create a `generate_distractors` function that produces plausible but incorrect options.
- [ ] **Persistence**: Add `save_assessment` and `load_assessment` functions to interact with the Postgres database.

### 2. Gap Analysis Engine
- [ ] **Taxonomy Mapping**: Implement a service in `src/assessment/analyzer.py` to map responses to the certification's domain/skill taxonomy.
- [ ] **Scoring Algorithm**: Develop the `calculate_gap_severity` function, incorporating correctness, confidence, and difficulty.
- [ ] **Remediation Planner**: Build a `create_remediation_plan` function that suggests learning objectives and content types.
- [ ] **Data Export**: Create an `export_to_json` and `export_to_csv` function for Google Sheets compatibility.

### 3. Validation & Quality Assurance
- [ ] **Coverage Validator**: Implement a `check_domain_coverage` function in `src/assessment/validator.py`.
- [ ] **Clarity & Uniqueness**: Add `check_question_clarity` and `check_duplicate_questions` heuristics.
- [ ] **Bias & Accessibility**: Develop an `audit_for_bias` function using automated checks for loaded language.
- [ ] **SME Override Hook**: Design a data structure and placeholder function for a manual SME review workflow.

### 4. API & Background Processing
- [ ] **API Endpoints**: Add the `POST /assess/request-assessment` and other required routes to `src/service/http.py`.
- [ ] **Background Worker**: Implement assessment generation as a FastAPI `BackgroundTasks` to avoid blocking.
- [ ] **State Management**: Update the `workflow_states` table in Postgres upon completion of generation and analysis tasks.
- [ ] **Idempotency**: Ensure that retrying a failed generation task does not create duplicate assessments.

### 5. Testing & Performance Assurance
- [ ] **Unit Tests**: Write pytest tests for all new functions in the generator, analyzer, and validator.
- [ ] **Contract Tests**: Update `specs/` to include contracts for the new assessment endpoints.
- [ ] **Integration Tests**: Create tests that simulate the full flow from `request-assessment` to gap analysis export.
- [ ] **Performance Harness**: Build a locust or similar load test to verify the <3-minute generation SLA.

### 6. Observability & Telemetry
- [ ] **Structured Logging**: Extend `src/common/jsonlog.py` to include context for assessment generation (e.g., `prompt_id`, `model_name`).
- [ ] **Metrics Collection**: Add Prometheus counters and histograms for generation time, validator rejection rate, and gap severity.
- [ ] **Dashboard Integration**: Create a new Grafana dashboard for "Assessment & Gap Analysis" metrics.
- [ ] **Alerting**: Define alerts in Prometheus/Alertmanager for high LLM error rates or generation latency spikes.

### 7. Parallel & Ongoing Streams Alignment
- [ ] **CI/CD Integration**: Add a new job to the CI/CD pipeline to run the assessment-related test suites.
- [ ] **Governance Review**: Schedule a weekly meeting with the governance team to review validator rejection rates and bias audit flags.
- [ ] **Backlog Grooming**: Create tickets for any performance bottlenecks or quality issues identified during testing.

## Dependencies & Inputs
- Stable Phase 1 ingestion pipeline with populated vector store and certification profiles.
- Access to OpenAI API (text generation + embeddings) and budget monitoring.
- SME feedback loops for question validation and gap analysis calibration.
- Observability stack components (Prometheus/Grafana/Elastic) configured in Phase 0/1.

## Risks & Mitigations
- **LLM Hallucinations**: Add validator checks, SME review loops, and keep knowledge retrieval context explicit.
- **Performance Overruns**: Profile generator steps, cache prompts, parallelize vector queries, and tune chunk counts.
- **Bias & Accessibility Issues**: Apply automated checks, maintain SME oversight, and document mitigation actions.
- **Integration Drift**: Regularly sync with Phase 3 workflow team to ensure data contracts remain compatible.

## Acceptance Criteria
- Assessment generator produces balanced 20-question sets per certification profile within 3 minutes under load.
- Gap analysis completes within 1 minute for standard assessments and outputs structured remediation plans.
- Validator rejects biased/invalid questions with actionable error messaging; acceptance rate ≥90% after tuning.
- API endpoints pass contract and integration tests; background workers handle retries without duplicate artifacts.
- Metrics dashboards and alerts operational, with documented runbooks for LLM failure handling and validator escalation.

## Team & Responsibilities
- **Assessment Lead Engineer**: Owns generator service, prompt design, and validator tooling.
- **Data Scientist / Learning Engineer**: Calibrates gap analysis algorithms, severity scoring, and remediation logic.
- **Backend Engineer**: Builds APIs, background workers, persistence layers, and integration tests.
- **QA Engineer**: Crafts test suites, performance harnesses, and automated regression checks.
- **Instructional Designer / SME**: Reviews question quality, ensures pedagogical alignment, and signs off on remediation plans.

## Exit Checklist
- [ ] Generator, analyzer, and validator modules merged with documentation and code comments.
- [ ] Assessment and gap analysis APIs deployed to staging with automated smoke tests.
- [ ] Performance benchmarks recorded showing SLA compliance (<3 minutes generation, <1 minute gap analysis).
- [ ] Observability dashboards updated with new metrics and alert thresholds; runbooks published.
- [ ] SME review completed for at least two certification profiles; feedback incorporated.
- [ ] All Phase 2 tickets closed or triaged to Phase 3 with clear owners and timelines.

## Handover Notes
- Summarize assessment quality metrics (difficulty distribution, validator rejection reasons) and outstanding optimization ideas.
- Provide list of open integration questions for workflow orchestration (data formats, retries, handoff triggers).
- Schedule Phase 3 kickoff with workflow/integration teams, ensuring they have sample payloads and API docs.