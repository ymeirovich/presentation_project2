# PresGen-Assess

AI-powered certification assessment and presentation generation with RAG-enhanced content and async workflow support.

## 🎯 Project Status

**✅ Phase 1 COMPLETE** - Foundation Infrastructure (Sept 23, 2025)
- FastAPI application with async workflow support
- RAG knowledge base with dual-stream architecture
- Database models and migrations (PostgreSQL + ChromaDB)
- CRUD APIs and comprehensive validation
- 40-slide presentation support with backend validation

**🚀 Phase 2 IN PROGRESS** - Assessment Engine & LLM Integration
- LLM service integration for assessment generation
- Gap analysis engine with confidence scoring
- PresGen-Core integration for presentation generation
- Comprehensive testing and validation suite

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

3. **Setup database**:
   ```bash
   # Create PostgreSQL database
   createdb presgen_assess

   # Run migrations
   alembic upgrade head
   ```

4. **Start application**:
   ```bash
   python3 main.py
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

- **`/api/v1/certifications/`**: CRUD operations for certification profiles
- **`/api/v1/knowledge/`**: Document upload and context retrieval
- **`/api/v1/assessments/`**: Assessment generation and results
- **`/api/v1/workflows/`**: Async workflow management with resume capability

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

- **Input Validation**: Comprehensive Pydantic schemas with pattern matching
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **CORS Protection**: Configurable CORS middleware
- **Request Logging**: Correlation ID tracking for audit trails
- **Data Encryption**: PostgreSQL encryption at rest
- **API Rate Limiting**: Built-in FastAPI rate limiting support

## Monitoring and Observability

- **Health Checks**: `/health` endpoint for system monitoring
- **Structured Logging**: JSON logs with correlation IDs
- **Performance Metrics**: Request timing and processing duration
- **Error Tracking**: Comprehensive exception handling and logging

## License

MIT License - see LICENSE file for details.