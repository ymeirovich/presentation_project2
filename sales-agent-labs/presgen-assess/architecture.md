# PresGen-Assess Architecture Document

## Table of Contents
- [System Overview](#system-overview)
- [Core Components](#core-components)
- [Data Architecture](#data-architecture)
- [Integration Layer](#integration-layer)
- [Workflow Engine](#workflow-engine)
- [Security Architecture](#security-architecture)
- [Performance Architecture](#performance-architecture)
- [Deployment Architecture](#deployment-architecture)

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PresGen-Assess Platform                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Frontend   │    │   API       │    │  Workflow   │    │   RAG       │  │
│  │  (Next.js)  │◄──►│  Gateway    │◄──►│ Orchestrator│◄──►│ Knowledge   │  │
│  │             │    │ (FastAPI)   │    │             │    │    Base     │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                   │                   │                   │        │
│         │                   │                   │                   │        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Google     │    │ Assessment  │    │   Content   │    │ Vector DB   │  │
│  │ Workspace   │    │  Generator  │    │ Generation  │    │ (ChromaDB)  │  │
│  │   APIs      │    │             │    │   Pipeline  │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                   │                   │                   │        │
│         │                   │                   │                   │        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Drive     │    │     Gap     │    │  PresGen    │    │ PostgreSQL  │  │
│  │   Forms     │    │  Analysis   │    │    Core     │    │  Database   │  │
│  │   Sheets    │    │   Engine    │    │   Avatar    │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Principles

1. **Microservices Architecture**: Modular components with clear separation of concerns
2. **Event-Driven Design**: Asynchronous workflow processing with state management
3. **Educational-First**: All technical decisions prioritize learning effectiveness
4. **RAG-Powered Intelligence**: Vector-based knowledge retrieval for assessment generation
5. **Integration-Centric**: Seamless integration with existing PresGen ecosystem

## Core Components

### 1. RAG Knowledge Base Engine

#### Component Architecture
```python
class RAGKnowledgeBase:
    """Central knowledge repository with vector search capabilities"""
    
    def __init__(self):
        self.vector_store = ChromaDB(
            collection_name="certification_knowledge",
            embedding_function=OpenAIEmbeddings()
        )
        self.document_processor = MultiFormatProcessor()
        self.chunk_strategy = SemanticChunker(
            chunk_size=1000,
            overlap=200,
            separators=["\n\n", "\n", ". ", " "]
        )
    
    async def ingest_certification_materials(
        self, 
        certification_id: str, 
        documents: List[DocumentInput]
    ) -> IngestionResult:
        """Process and embed certification materials"""
        
    async def retrieve_context(
        self, 
        query: str, 
        certification_filter: str,
        k: int = 5
    ) -> List[RetrievedChunk]:
        """Semantic search for relevant content"""
```

#### Storage Strategy
```
knowledge-base/
├── raw_documents/
│   ├── aws/
│   │   ├── exam_guides/
│   │   ├── whitepapers/
│   │   └── training_materials/
│   ├── azure/
│   └── gcp/
├── processed_chunks/
│   ├── {certification_id}/
│   │   ├── chunks.jsonl
│   │   └── metadata.json
└── embeddings/
    └── chroma_db/
        ├── index/
        └── collections/
```

### 2. Assessment Generation Engine

#### Multi-Dimensional Generator
```python
class AssessmentGenerator:
    """RAG-powered assessment creation with pedagogical validity"""
    
    def __init__(self):
        self.knowledge_base = RAGKnowledgeBase()
        self.prompt_manager = EducationalPromptManager()
        self.question_validator = QuestionQualityValidator()
        self.bloom_taxonomy = BloomsTaxonomyMapper()
    
    async def generate_comprehensive_assessment(
        self, 
        certification_profile: CertificationProfile,
        requirements: AssessmentRequirements
    ) -> Assessment:
        """Create multi-dimensional assessment using RAG context"""
        
        # Retrieve relevant knowledge base content
        contexts = await self._gather_domain_contexts(certification_profile)
        
        # Generate questions across Bloom's taxonomy levels
        questions = await self._generate_layered_questions(contexts)
        
        # Validate educational quality
        validated_questions = await self._validate_assessment_quality(questions)
        
        return Assessment(
            questions=validated_questions,
            metadata=self._generate_metadata(certification_profile),
            grading_rubric=self._create_grading_rubric(validated_questions)
        )
```

#### Question Generation Pipeline
```
Knowledge Base Query → Context Retrieval → Question Generation → Quality Validation → Distractor Creation → Educational Review
```

### 3. Gap Analysis Engine

#### Multi-Dimensional Analysis Framework
```python
class GapAnalysisEngine:
    """Sophisticated gap identification across learning dimensions"""
    
    def __init__(self):
        self.performance_analyzer = PerformancePatternAnalyzer()
        self.skill_mapper = SkillDomainMapper()
        self.confidence_assessor = ConfidenceIndicatorAnalyzer()
        self.learning_path_generator = PersonalizedPathGenerator()
    
    async def analyze_assessment_results(
        self, 
        results: AssessmentResults
    ) -> GapAnalysisReport:
        """Comprehensive gap analysis across multiple dimensions"""
        
        # Analyze performance patterns
        domain_gaps = self._analyze_domain_performance(results)
        cognitive_gaps = self._analyze_bloom_level_performance(results)
        confidence_gaps = self._analyze_confidence_indicators(results)
        
        # Identify specific skill deficiencies
        skill_gaps = await self._map_to_skill_deficiencies(
            domain_gaps, cognitive_gaps, confidence_gaps
        )
        
        # Generate targeted remediation plan
        remediation_plan = await self._generate_remediation_strategy(skill_gaps)
        
        return GapAnalysisReport(
            identified_gaps=skill_gaps,
            confidence_analysis=confidence_gaps,
            remediation_plan=remediation_plan,
            priority_ranking=self._prioritize_learning_needs(skill_gaps)
        )
```

#### Analysis Dimensions
```python
@dataclass
class LearningGap:
    """Multi-dimensional gap representation"""
    gap_type: GapType  # KNOWLEDGE, SKILL, APPLICATION, CONFIDENCE, DEPTH
    domain: str
    specific_skills: List[str]
    severity: float  # 0.0 to 1.0
    confidence_impact: float
    prerequisite_gaps: List[str]
    estimated_remediation_time: int  # minutes
    recommended_learning_modalities: List[str]
```

### 4. Workflow Orchestration Engine

#### State Machine Architecture
```python
class WorkflowOrchestrator:
    """Manages 11-step assessment and content generation workflow"""
    
    def __init__(self):
        self.state_manager = WorkflowStateManager()
        self.step_executor = StepExecutor()
        self.notification_service = NotificationService()
        self.error_handler = WorkflowErrorHandler()
    
    async def execute_assessment_workflow(
        self, 
        request: AssessmentRequest
    ) -> WorkflowExecution:
        """Execute complete assessment workflow with state tracking"""
        
        workflow_id = await self._initialize_workflow(request)
        
        # Execute workflow steps with state persistence
        for step in WORKFLOW_STEPS:
            try:
                result = await self._execute_step(workflow_id, step)
                await self._update_workflow_state(workflow_id, step, result)
            except Exception as e:
                await self._handle_step_failure(workflow_id, step, e)
                
        return await self._finalize_workflow(workflow_id)
```

#### Workflow State Management
```python
class WorkflowState:
    """Comprehensive workflow state tracking"""
    
    @dataclass
    class ExecutionState:
        workflow_id: UUID
        current_step: WorkflowStep
        step_states: Dict[WorkflowStep, StepState]
        google_resources: GoogleResourceSet
        generated_content: ContentCollection
        error_log: List[WorkflowError]
        created_at: datetime
        estimated_completion: datetime
        
    async def persist_state(self, state: ExecutionState) -> None:
        """Persist workflow state for recovery"""
        
    async def recover_workflow(self, workflow_id: UUID) -> ExecutionState:
        """Recover workflow from last successful checkpoint"""
```

## Data Architecture

### Database Schema Design

#### Core Tables
```sql
-- Certification knowledge base management
CREATE TABLE certification_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(100) NOT NULL,
    exam_domains JSONB NOT NULL,
    knowledge_base_path TEXT NOT NULL,
    assessment_template JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, version)
);

-- Document tracking for RAG system
CREATE TABLE knowledge_base_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    certification_profile_id UUID REFERENCES certification_profiles(id),
    original_filename VARCHAR(500) NOT NULL,
    stored_path TEXT NOT NULL,
    document_type VARCHAR(50) NOT NULL, -- PDF, DOCX, TXT
    file_size_bytes BIGINT NOT NULL,
    processing_status VARCHAR(50) DEFAULT 'pending',
    chunk_count INTEGER,
    embedding_model VARCHAR(100),
    processed_at TIMESTAMP,
    checksum VARCHAR(64), -- For duplicate detection
    created_at TIMESTAMP DEFAULT NOW()
);

-- Comprehensive workflow state tracking
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    certification_profile_id UUID REFERENCES certification_profiles(id),
    current_step VARCHAR(50) NOT NULL,
    execution_status VARCHAR(50) NOT NULL,
    
    -- Google Workspace resources
    google_form_id VARCHAR(255),
    google_sheet_id VARCHAR(255),
    google_drive_folder_id VARCHAR(255),
    
    -- Workflow data
    assessment_data JSONB,
    gap_analysis_results JSONB,
    training_plan JSONB,
    generated_content_urls JSONB,
    
    -- Metadata
    step_execution_log JSONB, -- Detailed step tracking
    error_log JSONB,
    performance_metrics JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    estimated_completion_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Assessment results and analysis
CREATE TABLE assessment_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_execution_id UUID REFERENCES workflow_executions(id),
    student_identifier VARCHAR(255) NOT NULL,
    
    -- Raw results
    responses JSONB NOT NULL, -- Question ID -> Response mapping
    completion_time_seconds INTEGER,
    submission_timestamp TIMESTAMP NOT NULL,
    
    -- Calculated metrics
    total_score FLOAT,
    domain_scores JSONB, -- Domain -> Score mapping
    bloom_level_scores JSONB, -- Cognitive level -> Score mapping
    confidence_indicators JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Gap analysis results
CREATE TABLE identified_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_result_id UUID REFERENCES assessment_results(id),
    gap_type VARCHAR(50) NOT NULL, -- KNOWLEDGE, SKILL, APPLICATION, etc.
    domain VARCHAR(255) NOT NULL,
    specific_skills TEXT[] NOT NULL,
    severity_score FLOAT NOT NULL, -- 0.0 to 1.0
    confidence_impact FLOAT,
    remediation_priority INTEGER,
    estimated_study_time_minutes INTEGER,
    recommended_modalities TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- Generated learning content tracking
CREATE TABLE learning_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_execution_id UUID REFERENCES workflow_executions(id),
    content_type VARCHAR(50) NOT NULL, -- presentation, avatar_video, outline
    topic VARCHAR(255) NOT NULL,
    target_gaps TEXT[], -- References to gap IDs
    
    -- Content URLs and metadata
    presgen_core_url TEXT,
    presgen_avatar_url TEXT,
    google_drive_url TEXT,
    public_access_url TEXT,
    
    generation_status VARCHAR(50) DEFAULT 'pending',
    generation_started_at TIMESTAMP,
    generation_completed_at TIMESTAMP,
    generation_error_log JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Vector Database Schema
```python
# ChromaDB collection structure
class CertificationKnowledgeCollection:
    """ChromaDB collection for certification knowledge"""
    
    collection_name = "certification_knowledge"
    
    metadata_schema = {
        "certification_id": str,
        "document_name": str,
        "chunk_index": int,
        "domain": str,
        "subdomain": str,
        "content_type": str,  # concept, example, procedure, etc.
        "bloom_level": str,   # remember, understand, apply, etc.
        "difficulty": float,  # 0.0 to 1.0
        "last_updated": str,
        "source_page": int
    }
```

## Integration Layer

### Google Workspace Integration

#### Architecture Pattern
```python
class GoogleWorkspaceManager:
    """Centralized Google Workspace integration"""
    
    def __init__(self):
        self.forms_client = GoogleFormsClient()
        self.sheets_client = GoogleSheetsClient()
        self.drive_client = GoogleDriveClient()
        self.permission_manager = PublicPermissionManager()
    
    async def create_assessment_workspace(
        self, 
        assessment: Assessment,
        workflow_id: UUID
    ) -> GoogleWorkspacePackage:
        """Create complete Google Workspace environment"""
        
        # Create organized folder structure
        folder = await self._create_assessment_folder(workflow_id)
        
        # Generate and deploy assessment form
        form = await self._create_assessment_form(assessment, folder.id)
        
        # Create results collection sheet
        sheet = await self._create_results_sheet(form.id, folder.id)
        
        # Configure public permissions
        await self._configure_public_access(form.id, sheet.id, folder.id)
        
        return GoogleWorkspacePackage(
            folder_id=folder.id,
            form_id=form.id,
            sheet_id=sheet.id,
            public_urls=self._generate_public_urls(form, sheet, folder)
        )
```

#### Permission Management
```python
class PublicPermissionManager:
    """Secure public access management"""
    
    async def configure_public_access(
        self, 
        resource_ids: List[str],
        permission_level: str = "reader"
    ) -> None:
        """Configure public access with appropriate restrictions"""
        
        for resource_id in resource_ids:
            await self.drive_client.permissions().create(
                fileId=resource_id,
                body={
                    'role': permission_level,
                    'type': 'anyone',
                    'allowFileDiscovery': False  # Security measure
                }
            ).execute()
```

### PresGen Module Integration

#### PresGen-Core Integration
```python
class PresGenCoreClient:
    """Integration with PresGen-Core for presentation generation"""
    
    def __init__(self):
        self.base_url = os.getenv('PRESGEN_CORE_URL')
        self.client = httpx.AsyncClient()
    
    async def generate_educational_presentation(
        self, 
        course_outline: CourseOutline,
        learning_objectives: List[str]
    ) -> PresentationResult:
        """Generate targeted educational presentation"""
        
        response = await self.client.post(
            f"{self.base_url}/presentations/educational",
            json={
                'title': course_outline.title,
                'content_outline': course_outline.sections,
                'learning_objectives': learning_objectives,
                'target_audience': 'certification_preparation',
                'difficulty_level': course_outline.difficulty,
                'estimated_duration': course_outline.duration_minutes
            }
        )
        
        return PresentationResult.from_response(response.json())
```

#### PresGen-Avatar Integration
```python
class PresGenAvatarClient:
    """Integration with PresGen-Avatar for video generation"""
    
    async def generate_educational_video(
        self, 
        presentation_url: str,
        narration_style: str = "instructor"
    ) -> VideoResult:
        """Generate avatar-narrated educational video"""
        
        response = await self.client.post(
            f"{self.base_url}/training/presentation-narration",
            json={
                'presentation_url': presentation_url,
                'voice_profile': narration_style,
                'educational_context': True,
                'pace': 'moderate',
                'emphasis_markers': True  # Highlight key concepts
            }
        )
        
        return VideoResult.from_response(response.json())
```

## Security Architecture

### Data Protection Strategy

#### Encryption and Security
```python
class SecurityManager:
    """Comprehensive security management"""
    
    def __init__(self):
        self.encryption_key = self._load_encryption_key()
        self.access_logger = AccessLogger()
        self.privacy_manager = PrivacyManager()
    
    async def encrypt_sensitive_data(self, data: dict) -> EncryptedData:
        """Encrypt PII and assessment data"""
        
    async def log_data_access(
        self, 
        user_id: str, 
        resource_type: str, 
        action: str
    ) -> None:
        """Audit trail for data access"""
        
    async def anonymize_assessment_data(
        self, 
        results: AssessmentResults
    ) -> AnonymizedResults:
        """Remove PII while preserving analytical value"""
```

#### Privacy Compliance
```python
class PrivacyComplianceManager:
    """GDPR/CCPA compliance management"""
    
    async def handle_data_deletion_request(self, user_id: str) -> None:
        """Process right to be forgotten requests"""
        
    async def export_user_data(self, user_id: str) -> UserDataExport:
        """Generate complete user data export"""
        
    async def audit_data_usage(self) -> DataUsageReport:
        """Generate privacy compliance audit report"""
```

## Performance Architecture

### Optimization Strategy

#### Caching Layer
```python
class PerformanceCacheManager:
    """Multi-level caching for performance optimization"""
    
    def __init__(self):
        self.redis_client = redis.Redis()
        self.local_cache = TTLCache(maxsize=1000, ttl=300)
        self.vector_cache = VectorSearchCache()
    
    async def cache_assessment_generation(
        self, 
        certification_id: str,
        assessment: Assessment
    ) -> None:
        """Cache generated assessments for reuse"""
        
    async def cache_vector_search_results(
        self, 
        query_hash: str,
        results: List[RetrievedChunk]
    ) -> None:
        """Cache vector search results"""
```

#### Performance Monitoring
```python
class PerformanceMonitor:
    """Real-time performance tracking"""
    
    async def track_workflow_performance(
        self, 
        workflow_id: UUID,
        step: WorkflowStep,
        duration: float
    ) -> None:
        """Track workflow step performance"""
        
    async def monitor_rag_performance(
        self, 
        query: str,
        retrieval_time: float,
        relevance_score: float
    ) -> None:
        """Monitor RAG system performance"""
```

### Scalability Design

#### Horizontal Scaling
```python
class ScalabilityManager:
    """Manage system scaling and load distribution"""
    
    async def scale_workflow_workers(self, load_factor: float) -> None:
        """Dynamically scale workflow processing capacity"""
        
    async def distribute_vector_search_load(
        self, 
        queries: List[str]
    ) -> List[SearchResult]:
        """Distribute vector search across multiple nodes"""
```

## Deployment Architecture

### Container Strategy
```dockerfile
# Dockerfile for PresGen-Assess
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Set up knowledge base directory
RUN mkdir -p /app/knowledge-base/{certifications,documents,embeddings}

EXPOSE 8000

CMD ["uvicorn", "src.service.http:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Infrastructure as Code
```yaml
# docker-compose.yml
version: '3.8'

services:
  presgen-assess:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/presgen_assess
      - CHROMA_DB_PATH=/app/knowledge-base/embeddings
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - db
      - chromadb
    volumes:
      - ./knowledge-base:/app/knowledge-base

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=presgen_assess
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

volumes:
  postgres_data:
  chroma_data:
```

### Monitoring and Observability
```python
class ObservabilityManager:
    """Comprehensive system monitoring"""
    
    def __init__(self):
        self.metrics_collector = PrometheusMetrics()
        self.log_aggregator = StructuredLogger()
        self.health_checker = HealthChecker()
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect comprehensive system performance metrics"""
        
    async def monitor_educational_effectiveness(self) -> EducationalMetrics:
        """Track learning outcome effectiveness"""
```

This architecture provides a robust, scalable foundation for PresGen-Assess while maintaining the educational focus and integration requirements specified in the requirements documents.