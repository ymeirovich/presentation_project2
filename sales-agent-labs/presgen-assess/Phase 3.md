# Phase 3 – Workflow Orchestration & Integrations (Weeks 8-10)

## Objectives
- Build the orchestrator that executes the 11-step PresGen-Assess workflow with resilient state management, retries, and auditability (`README.md:141`, `specification.md:63`).
- Integrate Google Workspace (Forms/Sheets/Drive) and PresGen modules (Core, Avatar) through hardened adapters, ensuring permission handling, rate-limit protection, and structured logging (`README.md:49`, `specification.md:24`).
- Deliver observability dashboards and operational runbooks that monitor workflow SLAs, API quotas, and integration health, feeding insights into ongoing improvement streams (`architecture.md:217`).

## Scope
- Orchestrator engine, workflow step registry, notification handling, and persistence under `src/workflow/`.
- Integration clients for Google Forms/Sheets/Drive and PresGen Core/Avatar residing in `src/integration/`.
- Error handling middleware, retry policies, and compensation logic for workflow resilience.
- Metrics, logging, and alerting for workflow execution and external API usage.
- Documentation and runbooks for operations and support teams.

## Out of Scope
- Assessment/gap analysis logic (Phase 2 deliverables).
- Frontend/dashboard updates (Phase 4 scope).
- New knowledge base ingestion features beyond bug fixes (Phase 1 scope).

## Deliverables
1. **Workflow Orchestrator**: Finite-state machine managing the full 11-step pipeline with persistence, retries, and audit trails (`src/workflow/orchestrator.py`, `workflow/status`).
2. **Step Implementations**: Modular step handlers and registry covering assessment generation, Google assets creation, monitoring, analysis, and delivery (`src/workflow/steps.py`).
3. **Integration Adapters**: Google Forms/Sheets/Drive clients, PresGen Core & Avatar connectors with structured logging, caching, and rate-limit resilience (`src/integration/*`).
4. **Error Handling & Notifications**: Centralized middleware, alerting hooks (email/Slack), and human-in-the-loop triggers for manual interventions (`specification.md:63`).
5. **Observability & Runbooks**: Metrics dashboards, log schemas, quota monitors, and operator documentation detailing recovery playbooks (`architecture.md:217`).

## Timeline & Milestones
- **Week 8 – Orchestrator Foundations**
  - Implement workflow state models, persistence hooks, and event bus abstractions.
  - Build step registry and execute mock steps end-to-end with dummy data.
  - Draft retry, timeout, and compensation strategies for each workflow phase.
- **Week 9 – Integrations & Resilience**
  - Develop Google Workspace clients with OAuth credential handling and rate-limit backoff.
  - Connect orchestrator steps to real services (Forms, Sheets, Drive, PresGen Core/Avatar) behind feature flags.
  - Add error handling middleware, alert hooks, and human override pathways.
- **Week 10 – Observability & Hardening**
  - Instrument workflows with metrics, traces, and structured logs; configure dashboards/alerts.
  - Execute integration tests and chaos simulations (API outages, partial failures) to validate recovery paths.
  - Finalize documentation, runbooks, and conduct dry runs with end-to-end pipelines.

## Detailed Workstreams
### 1. Orchestrator Engine
- [ ] **State Machine Design**: Define the `WorkflowStatus` enum in `src/models/workflow.py` with all 11 steps and failure states.
- [ ] **Persistence Layer**: Implement `create_workflow`, `update_workflow_status`, and `get_workflow` functions in the database repository.
- [ ] **Idempotency & Retries**: Wrap step execution logic with tenacity or a similar library to handle transient errors.
- [ ] **Compensation Logic**: For critical steps like resource creation, add `compensate_` methods to undo partial work on failure.
- [ ] **Notification Service**: Implement a `NotificationService` in `src/workflow/notifications.py` that can send emails or Slack messages.

### 2. Workflow Steps & Sequencing
- [ ] **Step Registry**: Create a dictionary or class in `src/workflow/orchestrator.py` to map `WorkflowStatus` enums to their handler functions.
- [ ] **Step Handlers**: Implement a separate function for each of the 11 workflow steps in `src/workflow/steps.py`.
- [ ] **Input/Output Contracts**: Define Pydantic models for the inputs and outputs of each step to ensure clear contracts.
- [ ] **Human-in-the-Loop**: For the `AWAITING_COMPLETION` step, implement a mechanism that pauses the workflow and can be resumed via an API call.

### 3. Google Workspace Integrations
- [ ] **Credential Management**: Implement a `load_google_credentials` function in `src/integration/google_auth.py` that securely loads credentials from the specified path.
- [ ] **Forms Client**: Build a `GoogleFormsClient` in `src/integration/google_forms.py` with `create_form` and `publish_form` methods.
- [ ] **Sheets Client**: Build a `GoogleSheetsClient` with `create_sheet`, `create_tab`, and `write_data` methods.
- [ ] **Drive Client**: Build a `GoogleDriveClient` with `create_folder` and `manage_permissions` methods.
- [ ] **Rate Limiting**: Use a library like `ratelimit` to decorate API calls and prevent hitting Google's rate limits.

### 4. PresGen Core & Avatar Integrations
- [ ] **Core Adapter**: Create a `PresGenCoreClient` in `src/integration/presgen_core.py` that can request presentation generation.
- [ ] **Avatar Adapter**: Create a `PresGenAvatarClient` in `src/integration/presgen_avatar.py` for video narration.
- [ ] **Status Polling**: Implement `poll_status` methods for both clients to asynchronously check for content generation completion.
- [ ] **Sanitized Logging**: Add logging to record request/response payloads, ensuring sensitive data is stripped.

### 5. Error Handling & Notifications
- [ ] **Centralized Middleware**: Create a FastAPI middleware to catch unhandled exceptions and trigger a generic workflow failure process.
- [ ] **Error Categorization**: In the orchestrator, add logic to distinguish between transient (e.g., network error) and permanent (e.g., invalid input) failures.
- [ ] **Notification Hooks**: Integrate the `NotificationService` into the orchestrator to send alerts on critical failures.
- [ ] **Runbook Documentation**: Create a `docs/runbooks/workflow_failures.md` file and document common error scenarios and their resolutions.

### 6. Observability & Operations
- [ ] **Metrics Instrumentation**: Add Prometheus metrics for step latency, retry counts, and external API errors.
- [ ] **Structured Logging**: Ensure all log messages within the `src/workflow/` and `src/integration/` directories include the `workflow_id`.
- [ ] **Dashboard Creation**: Build a "Workflow Orchestration" dashboard in Grafana to visualize the new metrics.
- [ ] **Alert Configuration**: Define alerts for when the P95 workflow duration exceeds the 30-minute SLA.

### 7. Parallel & Ongoing Streams Alignment
- [ ] **E2E Workflow Tests**: Create a new test suite in `tests/integration/test_workflow.py` that runs the full 11-step workflow with mock integrations.
- [ ] **Governance Check-in**: Add a standing agenda item to the weekly governance meeting to review integration error rates.
- [ ] **Backlog Prioritization**: Dedicate time in sprint planning to address any technical debt or performance issues from the workflow implementation.

## Dependencies & Inputs
- Stable Phase 2 outputs: assessment generation and gap analysis APIs operational.
- Google Workspace credentials and service accounts configured with required permissions.
- PresGen Core & Avatar endpoints accessible in staging environments with test content.
- Observability stack and alerting infrastructure from Phase 0/1 ready for integration.

## Risks & Mitigations
- **External API Quotas**: Implement quota monitoring, batch operations, and fallback queuing when near limits.
- **Credential Issues**: Automate token refresh, rotate credentials securely, and keep emergency break-glass procedures documented.
- **Workflow Complexity**: Use clear state diagrams, automated regression tests, and chaos simulations to surface edge cases early.
- **Integration Failures**: Provide manual fallback paths and feature flags to disable non-critical steps while keeping workflows running.

## Acceptance Criteria
- Full 11-step workflow executes successfully in staging, creating Google assets, running analysis, and delivering outputs.
- Orchestrator recovers from transient failures through retries and exposes clear error messages for permanent failures.
- Observability dashboards show workflow latency <30 minutes for 5-course generation, with alerts firing on SLA breaches.
- Integration adapters pass contract and integration tests, including simulated API outages and rate-limit scenarios.
- Runbooks validated through tabletop exercises; on-call engineers can follow procedures without gaps.

## Team & Responsibilities
- **Workflow Engineering Lead**: Orchestrator architecture, state management, and execution guarantees.
- **Integration Engineer**: Google Workspace and PresGen adapter implementations, credential handling.
- **DevOps/SRE**: Observability dashboards, alerting, chaos testing, and incident response readiness.
- **QA Engineer**: End-to-end workflow tests, error scenario coverage, UAT coordination.
- **Product/Program Manager**: Stakeholder communication, governance alignment, and cross-team coordination.

## Exit Checklist
- [ ] Orchestrator, step handlers, and integrations merged with documentation and feature flags.
- [ ] End-to-end workflow tests automated in CI/CD with nightly regression runs.
- [ ] Metrics dashboards and alerts validated against SLA targets; runbooks published and reviewed.
- [ ] Dry-run workflows executed with real integrations; issues triaged or resolved.
- [ ] Governance sign-off confirming compliance with constitution and quality gates.
- [ ] All Phase 3 action items closed or handed off to Phase 4 with clear owners and timelines.

## Handover Notes
- Summarize workflow execution metrics, integration reliability scores, and known limitations.
- Provide list of pending enhancements (e.g., advanced rerouting logic, improved notification UX) for Phase 4+ backlog.
- Schedule Phase 4 kickoff with experience and hardening teams, supplying sample payloads, API docs, and observability dashboards.