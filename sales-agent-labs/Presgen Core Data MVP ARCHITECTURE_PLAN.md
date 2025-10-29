# Presgen MVP Architecture Plan

## System Overview

### High-Level Architecture
```
User Input (Topic/Outline)
        ↓
┌─────────────────────────────────────────┐
│         PRESGEN CORE                    │
│  - Content Structuring Engine           │
│  - LLM Orchestration Layer              │
│  - Slide Generation Engine              │
│  - Template & Layout System             │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│         PRESGEN DATA                    │
│  - Web Search & Research API            │
│  - Data Retrieval Pipeline              │
│  - Fact Verification Layer              │
│  - Content Enrichment Engine            │
└─────────────────────────────────────────┘
        ↓
Output (PDF, PPTX, Interactive)
```

### Technology Stack
- **LLM Integration**: OpenAI GPT-4 (primary), Anthropic Claude (backup)
- **Backend**: Python 3.11+ (FastAPI/Flask)
- **Data Layer**: PostgreSQL + Redis (caching)
- **Search/Research**: Firecrawl API, Serper API
- **Document Generation**: python-pptx, reportlab
- **Infrastructure**: Docker, AWS/Railway

---

## Component Architecture

### Presgen Core

#### 1. Input Processing Layer
- **Parser**: Converts free-form input → structured outline
- **Validation**: Schema validation, content safety checks
- **Normalization**: Standardize topics, remove ambiguity

#### 2. LLM Orchestration
- **Prompt Engineering**: System prompts for slide generation (see `prompts.py`)
- **Multi-Agent Coordination**: Research agent → Content agent → Design agent
- **Token Management**: Chunking for long presentations, cost optimization
- **Fallback Strategy**: Primary LLM failure → secondary model

#### 3. Slide Generation Engine
- **Content Structuring**: Title, body, supporting points
- **Visual Layout**: Template selection based on content type
- **Design System**: Consistent typography, color schemes, spacing
- **Media Integration**: Image placement, chart generation

#### 4. Output Renderer
- **Formats**: PPTX (primary), PDF, HTML/interactive
- **Quality Control**: Readability checks, contrast validation
- **Export Pipeline**: Asynchronous rendering for large decks

### Presgen Data

#### 1. Research Pipeline
- **Query Formation**: Convert slide topics → search queries
- **Multi-Source Retrieval**:
  - Web search (Serper API)
  - Academic sources (optional: Semantic Scholar)
  - Company data (if B2B use case)
- **Deduplication**: Content similarity detection

#### 2. Fact Verification
- **Source Credibility Scoring**: Domain authority, publication date
- **Cross-Reference Validation**: Multi-source confirmation
- **Hallucination Detection**: Fact-checking prompts to LLM

#### 3. Content Enrichment
- **Statistics & Data Points**: Pull relevant numbers, trends
- **Visual Assets**: Image search, chart data extraction
- **Quote Extraction**: Pull authoritative quotes

#### 4. Caching Strategy
- **Redis Layer**: Query results cache (TTL: 24-48h)
- **PostgreSQL**: Long-term storage of verified data
- **Cache Invalidation**: Topic-based, time-based

---

## Integrations & Tools

### External APIs
- **OpenAI API**: GPT-4 for content generation
- **Anthropic Claude**: Backup LLM, fact verification
- **Firecrawl**: Web scraping and content extraction
- **Serper API**: Google search results
- **Unsplash/Pexels**: Stock images (free tier)

### Development Tools
- **Version Control**: Git + GitHub
- **CI/CD**: GitHub Actions (testing, linting)
- **Monitoring**: Sentry (error tracking), Datadog (performance)
- **Testing**: pytest, coverage reports

### Infrastructure
- **Containerization**: Docker for consistent environments
- **Hosting**: AWS (Lambda + S3) or Railway (simpler deployment)
- **Database**: AWS RDS (PostgreSQL), ElastiCache (Redis)
- **Storage**: S3 for generated presentations

---

## Security & Best Practices

### Security Measures
1. **API Key Management**:
   - Environment variables, never hardcoded
   - AWS Secrets Manager or similar
   - Key rotation policy

2. **Input Validation**:
   - Sanitize user inputs to prevent prompt injection
   - Rate limiting on API endpoints
   - Content safety filters (OpenAI Moderation API)

3. **Data Privacy**:
   - No storage of sensitive user data
   - GDPR compliance for EU users
   - User data encryption at rest (AES-256)

4. **Access Control**:
   - JWT-based authentication
   - Role-based permissions (if multi-user)
   - API rate limiting per user

### Best Practices Followed

#### Code Quality
- **Type Hints**: Full Python type annotations
- **Linting**: Ruff/Black for code formatting
- **Testing**: 80%+ code coverage target
- **Documentation**: Docstrings, API docs (Swagger)

#### LLM Engineering
- **Prompt Versioning**: Track prompt changes in Git
- **Temperature Control**: Lower for factual content, higher for creative
- **Output Validation**: JSON schema enforcement
- **Cost Monitoring**: Track token usage per request

#### Architecture Patterns
- **Separation of Concerns**: Core vs Data layers decoupled
- **Dependency Injection**: Easy testing, swappable components
- **Async/Await**: Non-blocking I/O for API calls
- **Circuit Breaker**: Graceful degradation on API failures

---

## Advanced Techniques

### 1. Multi-Agent Workflow
Based on `prompts.py`:
- **Research Agent**: Gathers data via Presgen Data
- **Content Agent**: Structures slides using MULTI_SLIDE_SYSTEM_PROMPT
- **Review Agent**: Quality checks, consistency validation

### 2. Retrieval-Augmented Generation (RAG)
- Embed slide topics → vector search for relevant cached content
- Reduces API calls, improves consistency
- Vector DB: Pinecone or pgvector (PostgreSQL extension)

### 3. Streaming Responses
- Real-time slide generation feedback to users
- SSE (Server-Sent Events) for progress updates
- Partial results displayed as generated

### 4. Template Learning
- Analyze successful presentations → extract patterns
- Fine-tune prompt templates based on user feedback
- A/B testing different prompt strategies

### 5. Content Chunking Strategy
- Break large presentations into batches (5-7 slides)
- Parallel processing where possible
- Maintain narrative consistency across chunks

---

## MVP Scope Definition

### ✅ In Scope (MVP v1.0)
1. **Core Features**:
   - Text input → 10-slide presentation
   - 3 pre-designed templates
   - PPTX export only
   - Web research integration (Firecrawl)
   - Basic fact verification

2. **Technical**:
   - Single LLM (GPT-4)
   - Simple REST API
   - SQLite database (upgrade to PostgreSQL later)
   - No user accounts (anonymous generation)

3. **Quality**:
   - Manual review of first 50 presentations
   - Basic error handling
   - Cost cap per generation ($0.50)

### ❌ Out of Scope (Future Versions)
- Multi-user authentication
- Real-time collaboration
- Advanced analytics/tracking
- Custom branding per user
- Video/audio integration
- Mobile app
- Fine-tuned models

---

## Technical Risks & Mitigation

| Risk | Impact | Mitigation Strategy |
|------|--------|---------------------|
| **LLM API Downtime** | High | Secondary LLM (Claude), cached fallback responses |
| **Cost Overruns** | High | Per-user rate limits, token budget enforcement |
| **Hallucinated Content** | Medium | Multi-source verification, confidence scoring |
| **Slow Generation (>60s)** | Medium | Async processing, progress indicators, caching |
| **Search API Rate Limits** | Low | Request queuing, multiple API providers |
| **Poor Slide Design** | Medium | Template library, design validation rules |

---

## Infrastructure & Costs (MVP)

### Estimated Monthly Costs
- **OpenAI API**: $200-500 (based on 500 presentations/month)
- **Firecrawl API**: $50 (starter plan)
- **Hosting (Railway)**: $20
- **Database (PostgreSQL)**: $15
- **Redis Cache**: $10
- **Monitoring/Logs**: $20
- **Total**: ~$315-615/month

### Scalability Considerations
- **Horizontal Scaling**: Stateless API design
- **Queue System**: Celery + Redis for background jobs
- **CDN**: CloudFront for static assets
- **Database Sharding**: By user_id (future)

---

## Development Timeline

### Phase 1: Core Engine (Weeks 1-3)
- [ ] Input parser + validation
- [ ] LLM integration (GPT-4)
- [ ] Basic slide generation (1 template)
- [ ] PPTX export

### Phase 2: Data Layer (Weeks 4-5)
- [ ] Web search integration
- [ ] Content extraction pipeline
- [ ] Basic fact verification
- [ ] Caching system

### Phase 3: Polish & Testing (Weeks 6-7)
- [ ] Add 2 more templates
- [ ] Error handling + logging
- [ ] Performance optimization
- [ ] User testing (10 beta users)

### Phase 4: Deployment (Week 8)
- [ ] Dockerize application
- [ ] Deploy to Railway/AWS
- [ ] Monitoring setup
- [ ] Documentation

---

## Competitive Differentiation

### Why Presgen Wins
1. **Research-First Approach**: Unlike Gamma/Beautiful.ai, we prioritize factual accuracy
2. **Multi-Agent Architecture**: Better narrative consistency than single-pass generation
3. **Customizable Intelligence**: Swap LLMs, adjust creativity vs accuracy
4. **Developer-Friendly**: API-first design for B2B integration

### Technical Moat
- Proprietary prompt engineering optimized for presentations
- Fact verification pipeline (hard to replicate)
- Template learning system
- Caching strategy reduces costs vs competitors

---

## Success Metrics

### MVP Success Criteria
- **Functionality**: 90% of presentations generated without errors
- **Quality**: 7/10 avg user rating on slide quality
- **Performance**: <60s generation time for 10 slides
- **Cost**: <$1 per presentation generation
- **Adoption**: 100 presentations generated in first month

### Technical KPIs
- API uptime: 99%+
- P95 response time: <45s
- LLM token efficiency: <15k tokens per presentation
- Cache hit rate: >40%

---

## Next Steps for CTO Review

1. **Validate Architecture**: Confirm technical approach is sound
2. **Review Cost Model**: Ensure pricing is sustainable
3. **Identify Gaps**: What concerns need addressing?
4. **Resource Planning**: Team size/skills needed
5. **Go/No-Go Decision**: Greenlight MVP or iterate plan

---

**Questions to Discuss**:
- Should we prioritize speed or quality for MVP?
- Self-hosted LLM option for enterprise clients?
- Build internal search vs rely on external APIs?
- OpenAI vs Anthropic as primary LLM provider?
