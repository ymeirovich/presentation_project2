# Gap Analysis → Avatar Narrated Presentations
## Project Plan Summary & Documentation Index

_Last updated: 2025-10-01_

---

## 📋 **Project Overview**

**Goal**: Automated end-to-end pipeline from assessment request to avatar-narrated presentation generation

**Timeline**: 10 weeks (Sprint 0 + 5 sprints × 2 weeks each)

**Status**: Sprint 0 Complete ✅ | Sprint 1 In Progress (20% complete) ⚠️

---

## 🗂️ **Documentation Structure**

This project plan is organized across multiple documents for clarity and modularity:

| Document | Purpose | Audience |
|----------|---------|----------|
| **[PROJECT_PLAN_SUMMARY.md](PROJECT_PLAN_SUMMARY.md)** (this file) | High-level overview and navigation | All stakeholders |
| **[CLARIFICATIONS_AND_ANALYSIS.md](CLARIFICATIONS_AND_ANALYSIS.md)** | Requirements clarifications and technical analysis | Technical leads, architects |
| **[DETAILED_SPRINT_PLAN.md](DETAILED_SPRINT_PLAN.md)** | Sprint 0 detailed implementation plan | Developers, QA engineers |
| **[SPRINT_1_5_IMPLEMENTATION.md](SPRINT_1_5_IMPLEMENTATION.md)** | Sprints 1-5 implementation details | Developers, QA engineers |
| **[GAP_TO_AVATAR_PROJECT_PLAN.md](GAP_TO_AVATAR_PROJECT_PLAN.md)** | Original high-level project plan | Product managers, executives |

---

## 🎯 **Key Requirements** (Updated)

### **1. Data Persistence Strategy**
✅ **Database-first approach**: All Gap Analysis data stored in PostgreSQL/SQLite
- Gap analysis results table
- Content outlines table (RAG-retrieved)
- Recommended courses table

✅ **On-demand Google Sheets export**: User clicks "Export to Sheets" button
- 4 tabs: Answers, Gap Analysis, Outline, Presentation
- No automatic sheet creation during workflow

### **2. AI Question Generation**
✅ **AIQuestionGenerator service exists** and is operational
- RAG-based question generation from certification resources
- Quality validation (min 8.0/10)
- Skill mapping to exam guide

✅ **Integration required**: Wire into workflow orchestrator
- Feature flag controlled
- Supports both AI generation and manual question upload

### **3. Gap Analysis Dashboard Enhancement**
✅ **Text summary**: Auto-generated plain language results explanation
✅ **Chart tooltips**: Context-specific interpretations on hover
✅ **Side panel**: Interpretation guide for all charts
✅ **Tabbed display**:
- Tab 1: Content Outline (skills mapped to RAG-retrieved resources)
- Tab 2: Recommended Courses (with "Generate Course" buttons)

### **4. PresGen-Avatar Integration**
✅ **Presentation-only mode**: Narrated slides (audio + slides → .mp4)
- No full avatar video (Video-only / Video-Presentation modes are future work)
- Timer tracker shows generation progress
- Launch Course button opens video player
- Download button for offline access

### **5. Course Generation Workflow**
```
Gap Analysis Dashboard
  ↓
User clicks "Generate Course" for skill gap
  ↓
Timer tracker starts (elapsed seconds)
  ↓
PresGen-Avatar API (Presentation-only mode)
  ↓
On completion: Launch + Download buttons appear
  ↓
Course link added to:
  - Google Sheet (Presentation tab)
  - Database (recommended_courses table)
```

---

## 🏗️ **Sprint Breakdown**

### **Sprint 0: Foundation & Bug Investigation** ✅ COMPLETE (Week 0)
**Goal**: Establish solid foundation for Sprints 1-5

**Key Deliverables**:
- [x] Feature flag implementation (7 flags)
- [x] Enhanced logging framework (StructuredLogger class)
- [x] Database schema migration (3 new tables)
- [x] Gap Analysis API parsing error investigation + fix
- [x] Service contract definitions (Pydantic schemas)

**Manual TDD Tests**: 4 tests (Feature flags, Logging, Database, API fix) - ✅ ALL PASSED

**Documentation**: [SPRINT_0_COMPLETION.md](GAP_TO_PRES_SPRINT_0_COMPLETION.md)

---

### **Sprint 1: AI Question Generation + Dashboard** ⚠️ IN PROGRESS (Weeks 1-2)
**Goal**: Integrate AI generation and enhance Gap Analysis Dashboard

**Progress**: 20% complete (1/5 major features)

**Key Deliverables**:
- [x] AIQuestionGenerator integrated into workflow orchestrator ✅
- [x] Gap Analysis Dashboard API endpoints created ✅
- [ ] Gap Analysis Database Persistence ❌ **BLOCKED**
- [ ] Text summary generation ⏸️ **BLOCKED**
- [ ] Content Outline RAG retrieval ❌ **NOT IMPLEMENTED**
- [ ] Recommended Courses generation ❌ **NOT IMPLEMENTED**

**Status**: Critical blocker - Gap analysis results not persisted to database. Sprint 2 cannot start until Sprint 1 complete.

**Manual TDD Tests**: 1/7 tests passing (AI generation only)

**Documentation**:
- Test Results: [GAP_TO_PRES_SPRINT_1_TDD_MANUAL_TESTING.md](GAP_TO_PRES_SPRINT_1_TDD_MANUAL_TESTING.md)
- Implementation Plan: [SPRINT_1_COMPLETION_PLAN.md](SPRINT_1_COMPLETION_PLAN.md) ⚠️ **NEW**
- Original Spec: [SPRINT_1_5_IMPLEMENTATION.md](SPRINT_1_5_IMPLEMENTATION.md#sprint-1)

---

### **Sprint 2: Google Sheets Export** (Weeks 3-4)
**Goal**: Implement on-demand 4-tab Google Sheets export

**Key Deliverables**:
- [ ] "Export to Sheets" button in Dashboard
- [ ] GoogleSheetsExportService with 4-tab generation
- [ ] RAG content formatting for Outline tab
- [ ] Rate limiter toggle (disabled in dev)
- [ ] Sheet population from database (not live data)

**Manual TDD Tests**: 4 tests (Export button, Sheet format, RAG content, Rate limiter)

**Documentation**: [SPRINT_1_5_IMPLEMENTATION.md](SPRINT_1_5_IMPLEMENTATION.md#sprint-2) (to be created)

---

### **Sprint 3: PresGen-Core Integration** (Weeks 5-6)
**Goal**: Generate presentations from gap analysis results

**Key Deliverables**:
- [ ] Content orchestration service
- [ ] Template selection algorithm
- [ ] Job queue with retries + circuit breaker
- [ ] Drive folder organization (certification/learner structure)
- [ ] Presentation tab updates in Google Sheet

**Manual TDD Tests**: 5 tests (Content orchestration, Template selection, Queue, Drive, Sheet update)

**Documentation**: [SPRINT_1_5_IMPLEMENTATION.md](SPRINT_1_5_IMPLEMENTATION.md#sprint-3) (to be created)

---

### **Sprint 4: PresGen-Avatar Integration** (Weeks 7-8)
**Goal**: Generate narrated presentations (Presentation-only mode)

**Key Deliverables**:
- [ ] PresGen-Avatar client (Presentation-only mode)
- [ ] Course generation from Dashboard
- [ ] Timer tracker UI component
- [ ] Video player integration
- [ ] Download functionality
- [ ] Sheet + database updates with course links

**Manual TDD Tests**: 4 tests (Course generation, Timer tracker, Video player, Download)

**Documentation**: [SPRINT_1_5_IMPLEMENTATION.md](SPRINT_1_5_IMPLEMENTATION.md#sprint-4) (to be created)

---

### **Sprint 5: Hardening & Pilot Launch** (Weeks 9-10)
**Goal**: Production readiness and pilot launch

**Key Deliverables**:
- [ ] Automated test suite (pytest + Playwright)
- [ ] Monitoring dashboards (Grafana/Prometheus)
- [ ] Performance optimization
- [ ] Security review (Drive permissions, API keys)
- [ ] Pilot launch with real users
- [ ] Rollback plan

**Manual TDD Tests**: 6 tests (E2E workflow, Load testing, Security audit, Rollback)

**Documentation**: [SPRINT_1_5_IMPLEMENTATION.md](SPRINT_1_5_IMPLEMENTATION.md#sprint-5) (to be created)

---

## 🔧 **Technical Architecture**

### **Database Schema (New Tables)**

```sql
-- Gap Analysis Results Storage
CREATE TABLE gap_analysis_results (
    id UUID PRIMARY KEY,
    workflow_id UUID REFERENCES workflow_executions(id),
    overall_score DECIMAL(5,2),
    total_questions INTEGER,
    correct_answers INTEGER,
    incorrect_answers INTEGER,
    skill_gaps JSONB,
    severity_scores JSONB,
    performance_by_domain JSONB,
    text_summary TEXT,
    charts_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Content Outline Storage (RAG-retrieved)
CREATE TABLE content_outlines (
    id UUID PRIMARY KEY,
    workflow_id UUID REFERENCES workflow_executions(id),
    skill_id VARCHAR(255),
    skill_name VARCHAR(500),
    exam_domain VARCHAR(255),
    exam_guide_section VARCHAR(500),
    content_items JSONB,  -- RAG retrieval results
    rag_retrieval_score DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Recommended Courses Storage
CREATE TABLE recommended_courses (
    id UUID PRIMARY KEY,
    workflow_id UUID REFERENCES workflow_executions(id),
    course_title VARCHAR(500),
    exam_domain VARCHAR(255),
    skills_covered JSONB,
    generation_status VARCHAR(50),  -- pending, generating, completed, failed
    video_url TEXT,
    download_url TEXT,
    duration_seconds INTEGER,
    generation_started_at TIMESTAMP,
    generation_completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### **Feature Flags**

```bash
# Sprint 1
FEATURE_ENABLE_AI_QUESTION_GENERATION=false
FEATURE_ENABLE_GAP_DASHBOARD_ENHANCEMENTS=false

# Sprint 2
FEATURE_ENABLE_SHEETS_EXPORT=false
FEATURE_ENABLE_RAG_CONTENT_RETRIEVAL=false

# Sprint 3
FEATURE_ENABLE_PRESGEN_CORE_INTEGRATION=false

# Sprint 4
FEATURE_ENABLE_PRESGEN_AVATAR_INTEGRATION=false

# Infrastructure
FEATURE_ENABLE_GOOGLE_RATE_LIMITER=false  # Keep false in dev
FEATURE_ENABLE_ENHANCED_LOGGING=true
```

### **API Endpoints (New)**

```
# Gap Analysis
GET  /api/v1/workflows/{workflow_id}/gap-analysis
GET  /api/v1/workflows/{workflow_id}/content-outlines
GET  /api/v1/workflows/{workflow_id}/recommended-courses

# Google Sheets Export
POST /api/v1/workflows/{workflow_id}/export-to-sheets

# Course Generation
POST /api/v1/courses/{course_id}/generate
GET  /api/v1/courses/{course_id}/status

# AI Question Generation (existing)
POST /api/v1/ai-questions/generate
```

---

## 📊 **Success Metrics**

### **Technical KPIs**
- [ ] AI question generation success rate >95%
- [ ] Gap analysis processing time <5 seconds
- [ ] Google Sheets export time <60 seconds
- [ ] Course generation time <10 minutes
- [ ] End-to-end workflow completion rate >90%

### **Business KPIs**
- [ ] User satisfaction with AI-generated questions >80%
- [ ] Gap Analysis Dashboard engagement >70%
- [ ] Sheets export usage >50% of workflows
- [ ] Course completion rate >60%
- [ ] Learning improvement (post-assessment) >20%

### **Operational KPIs**
- [ ] System uptime >99.5%
- [ ] Error rate <0.5%
- [ ] API response time p95 <500ms
- [ ] Database query time p95 <100ms
- [ ] Cost per workflow <$5

---

## 🚨 **Risks & Mitigations**

| Risk | Impact | Sprint | Mitigation |
|------|--------|--------|------------|
| AI generation quality issues | HIGH | 1 | Quality validation (min 8.0/10); fallback to manual |
| RAG retrieval accuracy low | MEDIUM | 1-2 | Manual content review; SME validation |
| Google API quota exhaustion | HIGH | 2 | Rate limiter; exponential backoff; preflight checks |
| PresGen-Core instability | MEDIUM | 3 | Circuit breaker; job queue with retries |
| Avatar generation failures | MEDIUM | 4 | Retry mechanism; manual override option |
| Database performance degradation | LOW | All | Proper indexing; query optimization; caching |

---

## 📝 **Key Decisions & Trade-offs**

### **Decision 1: Database-First Approach**
**Rationale**: Persist all data before export enables:
- Fast dashboard loading (no Google API dependency)
- On-demand export (user control)
- Historical data tracking
- Easier debugging and testing

**Trade-off**: Additional database storage (~1-5MB per workflow)

---

### **Decision 2: Presentation-Only Mode First**
**Rationale**: Simpler implementation:
- No video face animation complexity
- Faster generation (audio + slides only)
- Lower cost per course
- Easier QA validation

**Trade-off**: Less engaging than full avatar video (future enhancement)

---

### **Decision 3: Feature Flags for Gradual Rollout**
**Rationale**: Safe deployment strategy:
- Test each feature in isolation
- Easy rollback without code changes
- A/B testing capability
- Reduced blast radius for bugs

**Trade-off**: Additional configuration management overhead

---

## 👥 **Team Structure**

| Role | Allocation | Responsibilities |
|------|------------|------------------|
| **Senior Developer 1** | 100% (10 weeks) | Backend services, API endpoints, database |
| **Senior Developer 2** | 100% (10 weeks) | AI integration, RAG, PresGen integrations |
| **UI/UX Developer** | 80% (8 weeks) | Dashboard components, video player, UX |
| **QA Engineer** | 100% (10 weeks) | Manual TDD, automated tests, pilot validation |
| **DevOps Engineer** | 25% (2.5 weeks) | Infrastructure, monitoring, deployment |

**Total Effort**: ~4.05 FTE over 10 weeks

---

## 📅 **Milestone Schedule**

| Milestone | Week | Description | Review Gate |
|-----------|------|-------------|-------------|
| **M0: Foundation Complete** | 0 | Sprint 0 deliverables done | Technical review + QA sign-off |
| **M1: AI Generation Live** | 2 | Sprint 1 complete, Dashboard enhanced | Product review + user feedback |
| **M2: Sheets Export Ready** | 4 | Sprint 2 complete, Export functional | Integration testing complete |
| **M3: Presentations Generated** | 6 | Sprint 3 complete, PresGen-Core integrated | Performance validation |
| **M4: Courses Narrated** | 8 | Sprint 4 complete, Avatar integration done | E2E workflow validation |
| **M5: Production Launch** | 10 | Sprint 5 complete, Pilot successful | Stakeholder sign-off |

---

## 🎯 **Next Steps**

### **Immediate Actions** (This Week)
1. ✅ Review and approve project plan with stakeholders
2. ⏳ Assign team members to sprints
3. ⏳ Set up Sprint 0 kick-off meeting
4. ⏳ Prepare development environment (feature flags, database)
5. ⏳ Create JIRA/Linear tickets for Sprint 0 tasks

### **Week 0 (Sprint 0)**
- Implement feature flags
- Set up enhanced logging
- Migrate database schema
- Investigate Gap Analysis API bug
- Complete Sprint 0 manual TDD

### **Weeks 1-2 (Sprint 1)**
- Integrate AI question generation
- Build Gap Analysis Dashboard UI
- Implement RAG content retrieval
- Complete Sprint 1 manual TDD

---

## 📖 **Additional Resources**

- **API Documentation**: `/docs` endpoint (FastAPI auto-generated)
- **Database Schema**: `migrations/` directory
- **Test Data**: `tests/fixtures/` directory
- **Logging Examples**: `src/common/enhanced_logging_v2.py`
- **Feature Flags Config**: `.env.example` file

---

## 📞 **Support & Questions**

**Technical Questions**: Review [CLARIFICATIONS_AND_ANALYSIS.md](CLARIFICATIONS_AND_ANALYSIS.md)

**Sprint Details**: See individual sprint documentation files

**Bug Reports**: TBD (set up issue tracking)

---

**Project Status**: ✅ Planning Complete | 📅 Ready for Sprint 0 Kickoff

_Last updated: 2025-09-30 by Claude_