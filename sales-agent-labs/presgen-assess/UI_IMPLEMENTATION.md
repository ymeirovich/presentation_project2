# PresGen-Assess UI Integration Plan

**Last Updated:** 2025-09-22  
**Scope:** Align PresGen-Assess Phase 4 UI requirements with the shared PresGen UI (Next.js) application.

## Objectives
- Surface assessment workflows, gap analysis insights, and remediation assets alongside existing PresGen Core/Data/Video experiences in `presgen-ui`.
- Preserve the learning-first, assessment-integrity, and integration-excellence gates defined in `constitution.md`.
- Provide clear coordination points for backend services, design, QA, and deployment teams.

## Integration Overview
1. **Navigation & Layout**
   - Add a "PresGen-Assess" tab (or route) to the shared SegmentedTabs navigation (`presgen-ui/src/components/SegmentedTabs.tsx`, `app/page.tsx`).
   - Evaluate nested routing (`app/assess/page.tsx`) if state isolation is required for multi-step workflows.

2. **API Client Layer**
   - Create `src/lib/assess-api.ts` in `presgen-ui` with typed wrappers for:
     - `POST /assess/request-assessment`
     - `POST /assess/process-completion`
     - `GET /assess/workflow/{id}/status`
     - `POST /assess/workflow/{id}/notify-completion`
     - Document listing/metadata endpoints (`GET /documents`, etc.).
   - Reuse Zod schemas from `presgen-assess/src/schemas` to keep validation consistent.
   - Expose configuration via `NEXT_PUBLIC_ASSESS_API_URL` and optional auth headers.

3. **Feature Modules**
   - **Assessment Request Form**: React-hook-form + Zod, Markdown preview, document selector, validation parity with backend.
   - **Workflow Dashboard**: 11-step timeline, status badges, retry controls, filtered workflow list.
   - **Gap Analysis Views**: Domain/Bloom charts, remediation tables, export actions (CSV/Markdown/Sheets URLs).
   - **Learning Assets Panel**: Present generated presentations, avatar videos, Drive links with download/status actions.
   - **Operations Metrics**: Surface latency, retry counters, and alerts sourced from observability endpoints.

4. **Shared Experience Enhancements**
   - Centralize HTTP error handling, structured logging correlation IDs, and toast patterns.
   - Ensure accessibility (ARIA for charts/tables) and responsive behavior across breakpoints.
   - Maintain telemetry hooks so UX feedback feeds Phase 4 polish and backlog grooming (`Implementation.md`).

## Delivery Milestones
| Week | Focus | Key Outputs |
| --- | --- | --- |
| 1 | Navigation + Assessment Form | ✅ **Delivered (Week 1):** Tab added, assessment form with validation + API wiring |
| 2 | Workflow Dashboard | Timeline component, status polling, mock data stories |
| 3 | Gap Analysis & Assets | Visualization suite, export actions, integration tests |
| 4 | Hardening & Docs | Accessibility/Bias review, playbooks, deployment updates |

## Cross-Team Dependencies
- **Backend**: Stable assessment APIs and mock fixtures (`presgen-assess/specification.md`).
- **Design**: Visual specs for dashboards and gap charts; accessibility review.
- **DevOps**: Environment variables, staging URLs, observability dashboards.
- **QA**: Component + E2E test plans, data validation scripts.

## Testing Strategy
- Component tests (React Testing Library) for forms, dashboards, charts.
- Integration tests (Playwright/Cypress) covering assessment submission through gap review.
- Contract tests ensuring API changes remain synchronized with Zod schemas.

## Documentation & Deployment
- Update `presgen-ui/FRONTEND_DOCUMENTATION.md`, `DEPLOYMENT_GUIDE.md`, and `INTEGRATION_SUMMARY.md` with assess modules.
- Provide operator runbook for workflow monitoring and manual interventions.

## Next Actions
1. Kickoff with presgen-ui maintainers to validate timeline and resource availability.
2. Produce wireframes / UX prototypes for assessment dashboard states.
3. Stand up API stubs or mock server for frontend parallel development.

## Wireframe Snapshots (Textual)

These low-fidelity sketches guide component layout before high-fidelity design is delivered.

### Assessment Request Overview
```
┌───────────────────────────────────────────────┐
│ Header + Segmented Tabs (Core | Data | Assess)│
├───────────────────────────────────────────────┤
│ Assessment Form Card                          │
│  • Certification selector  • Document picker   │
│  • Markdown textarea       • Slide/question UX │
│  • Validation hints + Submit button            │
├───────────────────────────────────────────────┤
│ Recent Workflows (compact list with status)    │
└───────────────────────────────────────────────┘
```

### Workflow Timeline Dashboard
```
┌───────────────────────────────────────────────┐
│ Workflow filters/search + KPI chips           │
├───────────────────────────────────────────────┤
│ 11-step timeline (status dots, timestamps)    │
│ Retry / notify buttons on failure rows        │
├───────────────────────────────────────────────┤
│ Metrics strip (latency, retries, SLA alerts)  │
└───────────────────────────────────────────────┘
```

### Gap Analysis & Assets
```
┌───────────────────────────────────────────────┐
│ Summary KPIs (overall score, domains impacted)│
├───────────────────────────────────────────────┤
│ Charts row: domain severity | Bloom levels    │
├───────────────────────────────────────────────┤
│ Remediation table with export actions         │
├───────────────────────────────────────────────┤
│ Generated assets (slides, videos, sheets)     │
└───────────────────────────────────────────────┘
```
