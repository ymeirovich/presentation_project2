# PresGen-Assess

AI-powered certification assessment and presentation generation with RAG-enhanced content and async workflow support.

## 🎯 Project Status

**✅ Phase 1 COMPLETE** - Foundation Infrastructure (Sept 23, 2025)
- FastAPI application with async workflow support
- RAG knowledge base with dual-stream architecture
- Database models and migrations (PostgreSQL + ChromaDB)
- CRUD APIs and comprehensive validation
- 40-slide presentation support with backend validation

**✅ Phase 2 COMPLETE** - Assessment Engine & LLM Integration (Sept 23, 2025)
- LLM service integration for assessment generation
- Gap analysis engine with confidence scoring
- PresGen-Core integration for presentation generation
- Comprehensive testing and validation suite

**✅ Phase 3 COMPLETE** - API Layer & User Interface Development (Sept 23, 2025)
- Enterprise-grade REST API with 25+ endpoints
- JWT authentication with role-based permissions
- Rate limiting and security middleware
- Complete OpenAPI/Swagger documentation
- Production-ready deployment and integration testing

**🚀 Ready for Phase 4** - Frontend Development & Integration

## Features

- **Async Workflow Management**: Support for session breaks with Google Sheet URL resume capability
- **RAG-Enhanced Content**: Dual-stream knowledge base incorporating exam guides AND course transcripts
- **40-Slide Presentations**: Backend validation supporting 1-40 slide presentations
- **Comprehensive Assessment**: Multi-dimensional gap analysis with personalized learning paths
- **Knowledge Base Management**: Document processing, semantic chunking, and vector storage
- **REST API**: Complete FastAPI implementation with OpenAPI documentation

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 12+
- OpenAI API Key
- Google Cloud Project with enabled APIs

### Installation

1. **Clone and setup**:
   ```bash
   cd presgen-assess/
   pip3 install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Google Slides OAuth setup

PresGen-Core now authenticates to Google Slides with an OAuth client + user token pair:

1. Place your OAuth desktop credentials at `oauth_slides_client.json` (or update `OAUTH_CLIENT_JSON` in `.env`).
2. Generate/refresh the token before running the services:
   ```bash
   source .venv/bin/activate
   export PYTHONPATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs:$PYTHONPATH
   python src/agent/slides_google.py --auth
   ```
3. Confirm `token.json` exists at the path referenced by `OAUTH_TOKEN_PATH`.
4. Optional overrides:
   - `PRESGEN_CORE_VOICE_PROFILE` (default: `OpenAI Demo Voice (Your Audio)`)
   - `PRESGEN_CORE_QUALITY_LEVEL` (default: `fast`)
   - `PRESGEN_CORE_USE_CACHE` (default: `false`)

3. **Setup database**:
   ```bash
   # Create PostgreSQL database
   createdb presgen_assess

   # Run migrations
   alembic upgrade head
   ```

4. **Start application**:

   **Option A: Using the convenience script (recommended)**

   ```bash
   cd presgen-assess
   source .venv/bin/activate  # Activate virtualenv
   ./run_server.sh            # Development mode with auto-reload
   # OR
   ./run_server.sh --production  # Production mode without auto-reload
   ```

   **Option B: Manual start with PYTHONPATH**

   ```bash
   cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
   source .venv/bin/activate
   export PRESGEN_USE_MOCK=false
   export PYTHONPATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs:$PYTHONPATH
   cd presgen-assess
   uvicorn main:app --reload --port 8000
   ```

### Important: PYTHONPATH Requirement

The production presentation pipeline requires `src.agent.slides_google` from the parent `sales-agent-labs` directory.

**Key Points:**

- ✅ Use [run_server.sh](run_server.sh) - automatically sets PYTHONPATH
- ✅ Set PYTHONPATH before starting uvicorn manually
- ❌ Starting without PYTHONPATH causes `No module named 'src.agent'` errors

**Verify Google Slides module is importable:**

```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
source .venv/bin/activate
export PYTHONPATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs:$PYTHONPATH
python -c "import src.agent.slides_google"  # Should complete without error
```

**Multi-service startup for full stack:**

```bash
# Terminal 1: PresGen-Assess (port 8000)
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
source ../.venv/bin/activate
export OAUTH_CLIENT_JSON=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/oauth_slides_client.json
export OAUTH_TOKEN_PATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token.json
export PRESGEN_USE_MOCK=false
./run_server.sh


# Terminal 2: PresGen-Core (port 8080)
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
source .venv/bin/activate
export OAUTH_CLIENT_JSON=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/oauth_slides_client.json
export OAUTH_TOKEN_PATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token.json
export PYTHONPATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs:$PYTHONPATH
uvicorn src.service.http:app --reload --port 8080

# Terminal 4: PresGen-Avatar (port 8002)
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
source .venv/bin/activate
export OAUTH_CLIENT_JSON=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/oauth_slides_client.json
export OAUTH_TOKEN_PATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token.json
export PYTHONPATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs:$PYTHONPATH
export PRESGEN_USE_MOCK=false
uvicorn src.service.http:app --reload --port 8002

# Terminal 3: Frontend UI
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-ui
npm run dev
```

## Authentication

### Getting Started with Demo Token

```bash
# Get a demo token for testing
curl -X POST "http://localhost:8080/api/v1/auth/demo-token" \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user", "role": "educator"}'

# Use the token for authenticated requests
curl -X GET "http://localhost:8080/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Login with Credentials

```bash
# Login with existing user
curl -X POST "http://localhost:8080/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

## API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:8080/docs
- **ReDoc Documentation**: http://localhost:8080/redoc
- **Health Check**: http://localhost:8080/health

## Core Architecture

### Models

- **CertificationProfile**: Exam definitions with domain weightings
- **WorkflowExecution**: Async workflow state with resume tokens
- **AssessmentResult**: Multi-dimensional assessment outcomes
- **KnowledgeBaseDocument**: RAG document processing and indexing
- **IdentifiedGap**: Personalized learning gap analysis

### Services

- **RAGKnowledgeBase**: Dual-stream vector database (exam guides + transcripts)
- **DocumentProcessor**: PDF/DOCX/TXT processing with semantic chunking
- **VectorDatabaseManager**: ChromaDB integration with OpenAI embeddings

### API Endpoints

**Phase 1 Foundation APIs:**
- **`/api/v1/certifications/`**: CRUD operations for certification profiles
- **`/api/v1/knowledge/`**: Document upload and context retrieval
- **`/api/v1/assessments/`**: Assessment generation and results
- **`/api/v1/workflows/`**: Async workflow management with resume capability

**Phase 3 Service APIs:**
- **`/api/v1/auth/`**: JWT authentication and authorization
- **`/api/v1/llm/`**: LLM service for question generation and course outlines
- **`/api/v1/engine/`**: Assessment engine for comprehensive and adaptive assessments
- **`/api/v1/gap-analysis/`**: Learning gap identification and remediation planning
- **`/api/v1/presentations/`**: Personalized presentation generation and management

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/presgen_assess
CHROMA_DB_PATH=./knowledge-base/embeddings

# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=./config/google-service-account.json
GOOGLE_CLOUD_PROJECT=your-project-id

# PresGen Integration
PRESGEN_CORE_URL=http://localhost:8001
PRESGEN_CORE_MAX_SLIDES=40

# Workflow Settings
MAX_CONCURRENT_WORKFLOWS=10
WORKFLOW_RESUME_TOKEN_TTL_HOURS=72
```

## Development

### Running Tests

```bash
# Unit tests
make smoke-test

# Integration tests (requires GCP)
make live-smoke

# Format code
make fmt

# Lint code
make lint
```

### Database Management

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Adding New Certification

```bash
curl -X POST "http://localhost:8080/api/v1/certifications/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AWS Solutions Architect Associate",
    "version": "SAA-C03",
    "provider": "Amazon Web Services",
    "exam_domains": [
      {"name": "Design Resilient Architectures", "weight_percentage": 30, "topics": ["..."]},
      {"name": "Design High-Performing Architectures", "weight_percentage": 28, "topics": ["..."]},
      {"name": "Design Secure Architectures", "weight_percentage": 24, "topics": ["..."]},
      {"name": "Design Cost-Optimized Architectures", "weight_percentage": 18, "topics": ["..."]}
    ]
  }'
```

### Document Upload

```bash
curl -X POST "http://localhost:8080/api/v1/knowledge/upload" \
  -F "certification_id=aws-saa-c03" \
  -F "content_classification=exam_guide" \
  -F "files=@exam-guide.pdf" \
  -F "files=@course-transcript.txt"
```

## Async Workflow Example

1. **Start Assessment**:
   ```bash
   POST /api/v1/workflows/
   {
     "user_id": "user123",
     "certification_profile_id": "uuid-here",
     "workflow_type": "assessment_generation"
   }
   ```

2. **Resume with Sheet URL**:
   ```bash
   POST /api/v1/workflows/{workflow_id}/resume
   {
     "google_sheet_url": "https://docs.google.com/spreadsheets/d/abc123..."
   }
   ```

## Integration with PresGen-Core

PresGen-Assess integrates with the main PresGen system for 40-slide presentation generation:

- **Assessment Results** → **Gap Analysis** → **Personalized Course Content** → **40-Slide Presentations**
- **RAG Context** from knowledge base enhances all generated content
- **Source Citations** maintain traceability to exam guides and transcripts

## Security Features

**Authentication & Authorization:**
- **JWT Authentication**: Industry-standard token-based authentication
- **Role-Based Access Control**: Admin, educator, student, and API client roles
- **Demo Token System**: Secure testing and development access

**API Security:**
- **Rate Limiting**: 100 requests per 15-minute window per IP address
- **Input Validation**: Comprehensive Pydantic schemas with pattern matching
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **CORS Protection**: Configurable CORS middleware

**Infrastructure Security:**
- **Request Logging**: Correlation ID tracking for audit trails
- **Data Encryption**: PostgreSQL encryption at rest
- **Secure Headers**: Security middleware for production deployment
- **Error Handling**: Secure error responses without information leakage

## Monitoring and Observability

- **Health Checks**: `/health` endpoint for system monitoring
- **Structured Logging**: JSON logs with correlation IDs
- **Performance Metrics**: Request timing and processing duration
- **Error Tracking**: Comprehensive exception handling and logging

## License

MIT License - see LICENSE file for details.
