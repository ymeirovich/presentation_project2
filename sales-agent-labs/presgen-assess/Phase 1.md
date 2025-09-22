# Phase 1 – Knowledge Base & Data Layer (Weeks 1-3)

## Objectives
- Stand up the document ingestion and vector retrieval pipeline supporting PDF, DOCX, and TXT certification materials, backed by ChromaDB with Postgres metadata (`specification.md:18`, `presgen_assessment_prd.md:76`).
- Deliver certification profile CRUD APIs, domain modeling, and version control so downstream assessment services can rely on complete metadata (`specification.md:31`, `presgen_assessment_prd.md:108`).
- Establish automated test coverage, observability hooks, and operational runbooks that validate ingestion latency (<1 minute/100 pages) and retrieval performance (<500 ms for 5 chunks) before Phase 2 consumes the data (`presgen_assessment_prd.md:95`).

## Scope
- Knowledge base ingestion services, pipelines, and file-system organization under `knowledge-base/`.
- Data models, schemas, and migrations for certification profiles, documents, and workflow grounding tables.
- API endpoints, service objects, and repository layers in `src/knowledge/` and `src/models/` required for Phase 2.
- Test suites (unit, contract, integration) plus sample fixtures stored in `tests/` and `knowledge-base/certifications/`.
- Observability foundations (structured logging, metrics counters, latency histograms) covering ingestion and retrieval paths.

## Out of Scope
- Assessment/question generation logic (Phase 2).
- Gap analysis computation, remediation planning, or Google Workspace integrations (Phases 2-3).
- Frontend/dashboard work and avatar/presentation integration (Phase 4).

## Deliverables
1. **Ingestion Pipeline**: Async file processors with chunking, OpenAI embedding calls, and ChromaDB persistence (`src/knowledge/documents.py`, `src/knowledge/embeddings.py`).
2. **Metadata Persistence**: SQL migrations plus ORM/repository layer for certification profiles, uploaded document manifests, and ingestion audit logs (`specification.md:173`).
3. **Certification Profile API**: FastAPI routes, Pydantic schemas, and service layer enabling CRUD + material upload (`README.md:157`).
4. **Testing Suite**: Pytest-based unit, integration, and contract tests covering happy paths, invalid inputs, and performance thresholds (`README.md:62`).
5. **Operational Artifacts**: Runbooks detailing ingestion job execution, failure recovery, and monitoring dashboards for latency alerts (`architecture.md:217`).

## Timeline & Milestones
- **Week 1 – Foundations**
  - Scaffold `knowledge-base/` directory layout, sample certification assets, and ingestion configs.
  - Implement core document processors (PDF, DOCX, TXT) and chunking strategy with semantic overlap.
  - Draft initial SQL migrations and create Postgres schemas for certification profiles and documents.
- **Week 2 – Persistence & APIs**
  - Integrate ChromaDB client, embedder functions, and metadata persistence with transactional guarantees.
  - Build certification profile service + FastAPI routes (`src/knowledge/certifications.py`, `src/service/http.py`).
  - Seed sample profiles (AWS, Azure, GCP) and document fixtures to test ingestion end-to-end.
- **Week 3 – Testing & Hardening**
  - Author unit/integration/contract tests, including performance harness (<500 ms retrieval, <1 min ingestion).
  - Add structured logging, metrics, and dashboards/alerts for ingestion failures and latency breaches.
  - Perform dry-run ingestion of realistic certification guides, document findings, and close remaining defects.

## Detailed Workstreams
### 1. Document Ingestion & Embeddings
- Implement `DocumentProcessor` handling PDF via `PyPDF2`, DOCX via `python-docx`, and TXT fallback.
- Configure `RecursiveCharacterTextSplitter` (chunk size 1 000, overlap 200) to maintain semantic continuity (`specification.md:146`).
- Create async ingestion job that saves raw files to `knowledge-base/certifications/{profile}/` and stores chunk embeddings in ChromaDB with metadata (certification, domain, chunk index).
- Add checksum + timestamp tracking to detect re-ingestion needs and prevent duplicates.

### 2. Metadata & Database Layer
- Write Alembic migrations for `certification_profiles`, `knowledge_base_documents`, and `vector_ingestion_audit` tables (`specification.md:173`).
- Expose repository abstractions to query/update profiles, documents, and ingestion states.
- Integrate Postgres transactions ensuring profile creation + document ingestion either commit together or roll back on failure.

### 3. Certification Profile Management
- Define Pydantic models for create/update/read flows: includes version, exam domains, knowledge base references.
- Support document upload endpoint (`POST /assess/certifications/{cert_id}/upload-materials`) with validation for file type, size, and naming conventions.
- Provide list/detail endpoints with pagination and filtering to support future UI insights.

### 4. Testing & Quality Assurance
- Unit tests for chunking, embedding, repository operations, and Pydantic validation.
- Contract tests aligned with `specs/001-read-specification-md/contracts/document_api.yaml` ensuring API compatibility.
- Integration tests simulating full ingestion workflow, including failure modes (unsupported file, vector store outage).
- Performance tests using representative documents; capture metrics and assert SLA thresholds.

### 5. Observability & Operations
- Instrument ingestion/retrieval paths with latency histograms, throughput counters, and error rate metrics.
- Emit structured logs (`src/common/jsonlog.py`) capturing profile IDs, document names, and processing durations (`plan.md: Summary`).
- Draft runbooks covering: ingestion job execution, retry strategies, and ChromaDB maintenance.
- Configure alerts (Grafana/Prometheus) for ingestion latency breaches, embedding failures, and database capacity.

### 6. Parallel & Ongoing Streams Alignment
- Maintain continuous testing discipline: keep unit, integration, contract, performance, and security suites green in CI with automated coverage tracking hooks from Phase 0 governance (`README.md:62`, `presgen_assessment_prd.md:189`).
- Feed observability and telemetry insights back into backlog grooming by logging latency/throughput trends and creating follow-up tickets for Phase 2+ improvements (`README.md:171`, `presgen_assessment_prd.md:221`).
- Coordinate with product and ops leads on weekly checkpoints to review metrics, share lessons, and refine the roadmap without blocking Phase 2 kickoff.

## Dependencies & Inputs
- OpenAI embedding credentials available in `.env` (`README.md:97`).
- ChromaDB persistent store accessible at `knowledge-base/embeddings` (`README.md:58`).
- Postgres schema initialization from Phase 0 baseline (`Implementation.md`).
- Sample certification guides sourced via product team for AWS/Azure/GCP tracks.

## Risks & Mitigations
- **Embedding Cost Spikes**: Batch chunks and reuse cached embeddings; add rate limiting and cost monitoring.
- **Large File Timeouts**: Introduce streaming reads and asynchronous chunking with backpressure.
- **Schema Evolution**: Adopt migration versioning and backward-compatible changes to avoid breaking downstream services.
- **API Rate Limits (OpenAI)**: Implement exponential backoff, retry budgets, and fallback to queued processing.

## Acceptance Criteria
- Ingestion of a 100-page certification guide completes in under 60 seconds in staging.
- Retrieval of 5 relevant chunks for a standard query completes in under 500 ms.
- CRUD operations for certification profiles verified via API tests with 100% pass rate.
- All new modules achieve ≥85% unit test coverage; integration suite green in CI.
- Runbooks and dashboards reviewed with DevOps and documented in knowledge base.

## Team & Responsibilities
- **Backend Engineer (Lead)**: Document ingestion services, database migrations, API implementation.
- **Data Engineer**: ChromaDB management, embedding optimization, performance testing.
- **QA Engineer**: Test plan authoring, automation scripts, performance harness.
- **DevOps Engineer**: Observability setup, alerting configuration, staging deployment support.
- **Product/Instructional Designer**: Validate domain metadata, certification profile accuracy, educational integrity.

## Exit Checklist
- [ ] ChromaDB collections initialized with seeded certification documents.
- [ ] Postgres migrations applied; tables populated with sample data.
- [ ] API endpoints for certification profiles and document uploads deployed and documented.
- [ ] Test suites (unit, integration, contract, performance) pass in CI/CD pipeline.
- [ ] Monitoring dashboards live with documented alert thresholds.
- [ ] Operational runbooks stored in `docs/workflow.md` (or equivalent) and reviewed with stakeholders.

## Handover Notes
- Provide summary of ingestion metrics, data volume, and any outstanding technical debt tickets.
- List open questions or change requests that should roll into Phase 2 backlog.
- Schedule Phase 2 kickoff with assessment/gap analysis teams once acceptance criteria are signed off.
