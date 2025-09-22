# Tasks: Read Specification Document

**Input**: Design documents from `/Users/yitzchak/Documents/learn/presentation_project/presgen-assess/specs/001-read-specification-md/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → SUCCESS: Implementation plan loaded successfully
   → Extract: Python 3.11, FastAPI, pytest, file system access
2. Load optional design documents:
   → data-model.md: Extract entities → Document, DocumentAccessRequest, UserSession, AccessAuditLog
   → contracts/: document_api.yaml → 4 endpoints for contract tests
   → research.md: Extract decisions → secure file access, error handling patterns
3. Generate tasks by category:
   → Setup: dependencies, project structure
   → Tests: contract tests, integration tests for 6 scenarios
   → Core: models, services, API endpoints
   → Integration: FastAPI integration, error handling, logging
   → Polish: unit tests, performance validation, documentation
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001-T019)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests ✓
   → All entities have models ✓
   → All endpoints implemented ✓
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root (per plan.md)
- Paths relative to `/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess/`

## Phase 3.1: Setup
- [ ] T001 Create document reading project structure in existing src/ directory
- [ ] T002 Install additional dependencies: pathlib, typing extensions for Python 3.11
- [ ] T003 [P] Configure pytest for document reading module tests

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (from document_api.yaml)
- [ ] T004 [P] Contract test GET /documents/specification in tests/contract/test_specification_endpoint.py
- [ ] T005 [P] Contract test GET /documents/{document_name} in tests/contract/test_document_endpoint.py
- [ ] T006 [P] Contract test GET /documents/{document_name}/metadata in tests/contract/test_metadata_endpoint.py
- [ ] T007 [P] Contract test GET /documents in tests/contract/test_list_documents_endpoint.py

### Integration Tests (from quickstart.md scenarios)
- [ ] T008 [P] Integration test read specification success in tests/integration/test_read_specification_success.py
- [ ] T009 [P] Integration test read document as markdown in tests/integration/test_read_markdown_format.py
- [ ] T010 [P] Integration test get document metadata in tests/integration/test_document_metadata.py
- [ ] T011 [P] Integration test list available documents in tests/integration/test_list_documents.py
- [ ] T012 [P] Integration test document not found error in tests/integration/test_document_not_found.py
- [ ] T013 [P] Integration test invalid document name validation in tests/integration/test_invalid_document_name.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Data Models (from data-model.md entities)
- [ ] T014 [P] Document entity model in src/models/document.py
- [ ] T015 [P] DocumentAccessRequest model in src/models/access_request.py
- [ ] T016 [P] DocumentAccessResponse model in src/models/access_response.py
- [ ] T017 [P] UserSession model in src/models/user_session.py
- [ ] T018 [P] AccessAuditLog model in src/models/audit_log.py

### Services Layer
- [ ] T019 Document reading service in src/services/document_reader.py
- [ ] T020 Permission validation service in src/services/permission_manager.py
- [ ] T021 File system utilities in src/lib/file_utils.py

### API Endpoints (FastAPI integration)
- [ ] T022 GET /documents/specification endpoint in src/service/http.py
- [ ] T023 GET /documents/{document_name} endpoint in src/service/http.py
- [ ] T024 GET /documents/{document_name}/metadata endpoint in src/service/http.py
- [ ] T025 GET /documents endpoint in src/service/http.py

## Phase 3.4: Integration
- [ ] T026 Error handling middleware for document endpoints in src/service/http.py
- [ ] T027 Security validation for path traversal protection in src/services/document_reader.py
- [ ] T028 Access logging integration with existing logging system in src/common/jsonlog.py
- [ ] T029 Performance optimization with caching in src/services/document_reader.py

## Phase 3.5: Polish
- [ ] T030 [P] Unit tests for Document model in tests/unit/test_document_model.py
- [ ] T031 [P] Unit tests for file utilities in tests/unit/test_file_utils.py
- [ ] T032 [P] Unit tests for permission manager in tests/unit/test_permission_manager.py
- [ ] T033 Performance validation tests (<100ms response time) in tests/performance/test_document_reading_performance.py
- [ ] T034 [P] Update API documentation in docs/api.md
- [ ] T035 Security validation tests (path traversal, access control) in tests/security/test_document_security.py
- [ ] T036 Run quickstart validation scenarios in tests/integration/test_quickstart_scenarios.py

## Dependencies
### Phase Dependencies
- Setup (T001-T003) before all other phases
- Tests (T004-T013) before implementation (T014-T029)
- Models (T014-T018) before services (T019-T021)
- Services (T019-T021) before endpoints (T022-T025)
- Core implementation before integration (T026-T029)
- Everything before polish (T030-T036)

### Task Dependencies
- T014-T018 (models) can run in parallel
- T004-T013 (tests) can run in parallel
- T019 depends on T014-T018 (models complete)
- T020-T021 depend on T014-T018 (models complete)
- T022-T025 depend on T019-T021 (services complete)
- T026-T029 depend on T022-T025 (endpoints complete)
- T030-T036 depend on all implementation complete

## Parallel Example
```bash
# Launch model creation tasks together (T014-T018):
Task: "Create Document entity model in src/models/document.py"
Task: "Create DocumentAccessRequest model in src/models/access_request.py"
Task: "Create DocumentAccessResponse model in src/models/access_response.py"
Task: "Create UserSession model in src/models/user_session.py"
Task: "Create AccessAuditLog model in src/models/audit_log.py"

# Launch contract tests together (T004-T007):
Task: "Contract test GET /documents/specification in tests/contract/test_specification_endpoint.py"
Task: "Contract test GET /documents/{document_name} in tests/contract/test_document_endpoint.py"
Task: "Contract test GET /documents/{document_name}/metadata in tests/contract/test_metadata_endpoint.py"
Task: "Contract test GET /documents in tests/contract/test_list_documents_endpoint.py"

# Launch integration tests together (T008-T013):
Task: "Integration test read specification success in tests/integration/test_read_specification_success.py"
Task: "Integration test read document as markdown in tests/integration/test_read_markdown_format.py"
Task: "Integration test get document metadata in tests/integration/test_document_metadata.py"
Task: "Integration test list available documents in tests/integration/test_list_documents.py"
Task: "Integration test document not found error in tests/integration/test_document_not_found.py"
Task: "Integration test invalid document name validation in tests/integration/test_invalid_document_name.py"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task or logical group
- Follow existing PresGen-Assess code patterns
- Maintain <100ms performance requirement
- Ensure security validation throughout

## Task Generation Rules Applied
1. **From Contracts**: 4 contract files → 4 contract test tasks [P]
2. **From Data Model**: 5 entities → 5 model creation tasks [P]
3. **From User Stories**: 6 quickstart scenarios → 6 integration tests [P]
4. **From Research**: Security patterns → security validation tasks
5. **Ordering**: Setup → Tests → Models → Services → Endpoints → Integration → Polish

## Validation Checklist
- [x] All contracts have corresponding tests (T004-T007)
- [x] All entities have model tasks (T014-T018)
- [x] All tests come before implementation (T004-T013 before T014+)
- [x] Parallel tasks truly independent (different files)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] Performance requirements included (T033)
- [x] Security requirements included (T035)
- [x] Integration with existing codebase (T022-T025, T028)

## Estimated Timeline
- **Phase 3.1 (Setup)**: 2 hours
- **Phase 3.2 (Tests)**: 8 hours
- **Phase 3.3 (Core)**: 12 hours
- **Phase 3.4 (Integration)**: 6 hours
- **Phase 3.5 (Polish)**: 4 hours
- **Total**: ~32 hours (4 working days)

**Ready for implementation execution following TDD principles.**