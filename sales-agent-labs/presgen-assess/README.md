# PresGen-Assess

> Adaptive learning assessment platform with AI-powered gap analysis and personalized content generation

PresGen-Assess transforms certification preparation through intelligent assessment, multi-dimensional gap analysis, and automated generation of targeted learning content using the PresGen ecosystem. Features async workflow support with Sheet URL resume capability, RAG-enhanced content generation, and support for up to 40-slide presentations.

## 🎯 Core Features

- **RAG-Enhanced Assessment Generation**: Create comprehensive quizzes using both exam guides AND course transcripts from certification knowledge base
- **Async Workflow Support**: Resume workflow with Google Sheet URL after external assessment completion
- **Multi-Dimensional Gap Analysis**: Identify specific knowledge, skill, and application gaps with 85%+ accuracy
- **40-Slide Presentation Support**: Generate comprehensive presentations with 1-40 slide range and backend validation
- **Automated Content Pipeline**: Generate personalized presentations and avatar videos targeting identified deficiencies with source citations
- **Google Workspace Integration**: Seamless deployment via Google Forms, Sheets, and Drive with public access
- **Workflow Orchestration**: 12-step automated process with async break point for human completion

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ RAG Knowledge   │    │ Assessment      │    │ Gap Analysis    │
│ Base (ChromaDB) │───▶│ Generator       │───▶│ Engine          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Certification   │    │ Google Forms    │    │ Training Plan   │
│ Profiles        │    │ Deployment      │    │ Generation      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ PresGen-Core    │    │ PresGen-Avatar  │    │ Public Resource │
│ Integration     │───▶│ Integration     │───▶│ Links           │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 Project Structure

```
presgen-assess/
├── src/
│   ├── assessment/          # Multi-dimensional assessment generation
│   │   ├── generator.py     # Quiz creation with RAG context
│   │   ├── analyzer.py      # Gap analysis and response processing
│   │   └── validator.py     # Assessment quality assurance
│   ├── knowledge/           # RAG knowledge base implementation
│   │   ├── base.py          # Vector database operations
│   │   ├── certifications.py # Certification profile management
│   │   └── embeddings.py    # Document processing and embeddings
│   ├── integration/         # External service integrations
│   │   ├── google_forms.py  # Forms API integration
│   │   ├── google_sheets.py # Sheets API integration
│   │   ├── presgen_core.py  # Core module integration
│   │   └── presgen_avatar.py # Avatar module integration
│   ├── workflow/            # Workflow orchestration
│   │   ├── orchestrator.py  # Main workflow management
│   │   └── steps.py         # Individual workflow steps
│   └── models/              # Data models and schemas
├── knowledge-base/          # Vector database and certification materials
│   ├── certifications/      # AWS, Azure, GCP materials
│   ├── documents/           # Uploaded exam guides
│   └── embeddings/          # Vector embeddings storage
├── config/                  # Configuration and templates
│   ├── certifications.yaml  # Certification profiles
│   └── prompts.yaml         # Assessment generation prompts
└── tests/                   # Test suite
    ├── unit/
    ├── integration/
    └── fixtures/
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- ChromaDB
- Google Workspace API credentials
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd presgen-assess
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   npm install
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and database settings
   ```

4. **Initialize database**
   ```bash
   python scripts/init_database.py
   ```

5. **Set up knowledge base**
   ```bash
   python scripts/setup_knowledge_base.py
   ```

6. **Start the services**
   ```bash
   # Backend
   python -m uvicorn src.service.http:app --reload --port 8000
   
   # Frontend
   npm run dev
   ```

### First Assessment

1. **Upload certification materials**
   ```bash
   curl -X POST "http://localhost:8000/assess/certifications" \
     -F "name=AWS Solutions Architect" \
     -F "description=SAA-C03 preparation" \
     -F "exam_guide=@aws-saa-exam-guide.pdf"
   ```

2. **Generate assessment**
   ```bash
   curl -X POST "http://localhost:8000/assess/request-assessment" \
     -H "Content-Type: application/json" \
     -d '{"certification_id": "cert-uuid", "user_id": "user123"}'
   ```

3. **Monitor workflow**
   Visit the assessment dashboard to track progress and access generated resources.

## 🔄 12-Step Async Workflow Process

1. **Request Assessment** - User initiates assessment for specific certification
2. **Generate Assessment** - RAG system creates comprehensive quiz using exam guides + course transcripts
3. **Deploy Google Form** - Public assessment form with integrated grading
4. **Create Drive Resources** - Organized folder structure for all materials
5. **Return URLs to User** - User receives Form/Sheet links, workflow pauses
6. **ASYNC BREAK** - User completes assessment externally, may close application
7. **Resume with Sheet URL** - User returns and provides completed assessment Sheet URL
8. **Analyze Results** - Multi-dimensional gap analysis with RAG context
9. **Generate Training Plan** - Personalized learning path using knowledge base sources
10. **Create Course Outlines** - Detailed outlines with RAG source citations
11. **Generate Presentations** - PresGen-Core creates 1-40 slide targeted content with sources
12. **Produce Avatar Videos** - PresGen-Avatar generates narrated content for any slide count
13. **Finalize Resources** - Public links and organized access to all materials

## 📊 API Reference

### Assessment Management

```python
# Request new assessment workflow
POST /assess/request-assessment
{
  "certification_id": "uuid",
  "user_id": "string",
  "custom_requirements": "string",
  "slide_count": 20  # 1-40 range supported
}

# Resume workflow with completed assessment
POST /assess/resume-workflow
{
  "workflow_id": "uuid",
  "sheet_url": "string",
  "user_id": "string"
}

# Process completed assessment (legacy endpoint)
POST /assess/process-completion
{
  "workflow_id": "uuid",
  "sheet_url": "string"
}

# Check workflow status
GET /assess/workflow/{workflow_id}/status

# Validate Google Sheets URL
POST /assess/validate-sheet-url
{
  "sheet_url": "string"
}
```

### Certification Profiles

```python
# List available certifications
GET /assess/certifications

# Create new certification profile
POST /assess/certifications
{
  "name": "string",
  "version": "string", 
  "exam_guide": "file"
}

# Upload additional materials
POST /assess/certifications/{cert_id}/upload-materials
```

### Knowledge Base

```python
# Ingest new documents
POST /assess/knowledge-base/ingest
{
  "certification_id": "uuid",
  "documents": ["file1", "file2"]
}

# Search knowledge base
GET /assess/knowledge-base/{cert_id}/search?q=query
```

## 🧪 Testing

### Unit Tests
```bash
pytest tests/unit/ -v
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### End-to-End Tests
```bash
pytest tests/e2e/ -v --slow
```

### Performance Tests
```bash
python tests/performance/workflow_benchmarks.py
```

## 📈 Performance Targets

- **Assessment Generation**: <3 minutes including RAG retrieval from exam guides + transcripts
- **Gap Analysis Processing**: <1 minute for 20-question assessment with RAG context
- **Presentation Generation**: <15 seconds per slide (up to 40 slides = 10 minutes max)
- **Avatar Video Generation**: <22 seconds per slide (up to 40 slides = 15 minutes max)
- **Complete Workflow**: <45 minutes for 5-course generation with 40-slide presentations
- **RAG Retrieval**: <500ms for 5 relevant document chunks with source attribution
- **Knowledge Base Search**: >85% relevance for assessment generation with dual-source context
- **Async Resume**: <2 seconds to validate Sheet URL and resume workflow

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/presgen_assess
CHROMA_DB_PATH=./knowledge-base/embeddings

# API Keys
OPENAI_API_KEY=your_openai_key
GOOGLE_CREDENTIALS_PATH=./config/google-credentials.json

# PresGen Integration (40-slide support)
PRESGEN_CORE_URL=http://localhost:8001
PRESGEN_AVATAR_URL=http://localhost:8002
PRESGEN_CORE_MAX_SLIDES=40
PRESGEN_AVATAR_MAX_SLIDES=40

# Workflow Settings (Async-aware)
MAX_CONCURRENT_WORKFLOWS=10
ASSESSMENT_TIMEOUT_MINUTES=60
ASYNC_WORKFLOW_ENABLED=true
WORKFLOW_RESUME_TOKEN_TTL_HOURS=72
MAX_SLIDES_SUPPORTED=40

# Performance Settings
PRESENTATION_GENERATION_TIMEOUT_SECONDS=600  # 10 minutes for 40 slides
AVATAR_GENERATION_TIMEOUT_SECONDS=900       # 15 minutes for 40 slides
RAG_SOURCE_CITATION_REQUIRED=true
```

### Certification Profiles

```yaml
# config/certifications.yaml
aws_saa:
  name: "AWS Solutions Architect Associate"
  version: "SAA-C03"
  domains:
    - name: "Design Resilient Architectures"
      weight: 30
      skills: ["High availability", "Fault tolerance", "Disaster recovery"]
    - name: "Design High-Performing Architectures"
      weight: 28
      skills: ["Storage solutions", "Compute solutions", "Networking"]
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch** (`git checkout -b feature/amazing-feature`)
3. **Run tests** (`pytest tests/`)
4. **Commit changes** (`git commit -m 'Add amazing feature'`)
5. **Push to branch** (`git push origin feature/amazing-feature`)
6. **Open Pull Request**

### Development Guidelines

- Follow pedagogical principles in all assessment features
- Maintain >90% test coverage for core modules
- Ensure gap analysis accuracy >85% through validation
- Document all workflow steps and integration points
- Validate educational effectiveness before feature release

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: support@presgen-assess.com

## 🗺️ Roadmap

### Phase 1 (Current)
- [x] RAG knowledge base implementation
- [x] Workflow orchestration system
- [x] Google Workspace integration
- [ ] Multi-dimensional gap analysis
- [ ] PresGen module integration

### Phase 2 (Q2 2025)
- [ ] Advanced analytics and learning insights
- [ ] Real-time adaptive assessments
- [ ] Mobile application
- [ ] Enterprise LMS integration

### Phase 3 (Q3 2025)
- [ ] Simulation-based assessments
- [ ] AI-powered tutoring system
- [ ] Collaborative learning features
- [ ] Global localization support

---

**Built with ❤️ for better learning outcomes**

For more information, see the [Product Requirements Document](docs/prd.md) and [Technical Specification](docs/specification.md).