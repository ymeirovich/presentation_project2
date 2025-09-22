# PresGen-Assess Implementation Plan (Updated)

## Executive Summary

This implementation plan details the development approach for PresGen-Assess, an adaptive learning assessment platform that integrates with the existing PresGen ecosystem. The system features async workflow support with Sheet URL resume capability, RAG-enhanced content generation using exam guides and course transcripts, and support for up to 40-slide presentations. The plan follows a 12-week timeline divided into four phases, each with specific deliverables, milestones, and success criteria.

## Strategic Implementation Approach

### Development Philosophy
- **Educational-First**: All technical decisions prioritize learning effectiveness
- **RAG-Enhanced**: Mandatory use of certification-specific knowledge base (exam guides + course transcripts)
- **Async-Aware**: Workflow supports session breaks with Sheet URL resume capability
- **Scale-Ready**: Backend validation and UI support for 1-40 slide presentations
- **Incremental Delivery**: Working functionality delivered at each phase
- **Risk-Driven**: Address highest-risk components early
- **Integration-Focused**: Seamless integration with existing PresGen modules
- **Quality-Assured**: Comprehensive testing and validation at each step

### Success Metrics
- **Technical**: Assessment generation <3 minutes with RAG citations, gap analysis >85% accuracy, 40-slide presentation support
- **Educational**: >20% improvement in post-assessment scores, source attribution in all content
- **Business**: 50% reduction in learning time vs traditional methods, seamless async workflow

## Required API Permissions & Setup

### Google Cloud Platform APIs
**Required Services:**
1. **Google Forms API** (`forms.googleapis.com`)
   - Scope: `https://www.googleapis.com/auth/forms`
   - Permissions: Create/update forms, manage responses, publish forms

2. **Google Sheets API** (`sheets.googleapis.com`)
   - Scope: `https://www.googleapis.com/auth/spreadsheets`
   - Permissions: Create/read/write spreadsheets, manage sheets and tabs

3. **Google Drive API** (`drive.googleapis.com`)
   - Scope: `https://www.googleapis.com/auth/drive`
   - Permissions: Create folders, manage file permissions, upload/download files

**Setup Steps:**
```bash
# 1. Enable APIs in Google Cloud Console
gcloud services enable forms.googleapis.com
gcloud services enable sheets.googleapis.com
gcloud services enable drive.googleapis.com

# 2. Create Service Account
gcloud iam service-accounts create presgen-assess-service \\
  --display-name="PresGen Assess Service Account"

# 3. Generate credentials file
gcloud iam service-accounts keys create ./config/google-service-account.json \\
  --iam-account=presgen-assess-service@YOUR-PROJECT-ID.iam.gserviceaccount.com

# 4. Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=./config/google-service-account.json
```

### OpenAI API Configuration
**Required Access:**
- **API Key**: GPT-4 + Embeddings access
- **Model Access**: `gpt-4`, `text-embedding-3-small`
- **Rate Limits**: Tier 2+ recommended (higher RPM/TPM limits)
- **Budget Alerts**: Set spending limits and monitoring

**Environment Setup:**
```bash
export OPENAI_API_KEY=your_openai_api_key
export OPENAI_ORG_ID=your_organization_id  # Optional but recommended
```

### PresGen Module API Integration
**PresGen-Core API:**
- Endpoint: `http://localhost:8001/presentations/educational`
- **NEW REQUIREMENT**: Must support `max_slides: 40` parameter
- Authentication: Internal service token
- Timeout: 600 seconds (extended for 40-slide presentations)

**PresGen-Avatar API:**
- Endpoint: `http://localhost:8002/training/presentation-narration`
- **NEW REQUIREMENT**: Must handle presentations up to 40 slides
- Authentication: Internal service token
- Timeout: 900 seconds (extended for longer content)

### Database Permissions
**PostgreSQL Setup:**
```sql
-- Create database and user
CREATE DATABASE presgen_assess;
CREATE USER presgen_assess_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE presgen_assess TO presgen_assess_user;
```

**ChromaDB Setup:**
```bash
# Persistent storage directory
mkdir -p ./knowledge-base/embeddings
chmod 755 ./knowledge-base/embeddings
```

## Phase 1: Foundation Infrastructure (Weeks 1-3)

### Week 1: RAG Knowledge Base Foundation

#### Objectives
- Establish vector database infrastructure
- Implement document processing pipeline
- Create basic certification profile management

#### Technical Tasks

**Day 1-2: Project Setup**
```bash
# Initialize project structure
mkdir -p presgen-assess/{src,tests,config,knowledge-base}
cd presgen-assess

# Set up Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Initialize database schema
python scripts/init_database.py
```

**Day 3-4: ChromaDB Integration**
```python
# src/knowledge/embeddings.py
class VectorDatabaseManager:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path="./knowledge-base/embeddings"
        )
        self.collection = self.client.get_or_create_collection(
            name="certification_knowledge",
            embedding_function=embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="text-embedding-3-small"
            )
        )
    
    async def store_document_chunks(
        self, 
        chunks: List[str], 
        metadata: List[dict]
    ) -> bool:
        """Store processed document chunks with metadata"""
        try:
            self.collection.add(
                documents=chunks,
                metadatas=metadata,
                ids=[f"chunk_{i}" for i in range(len(chunks))]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            return False
```

**Day 5: Document Processing Pipeline**
```python
# src/knowledge/documents.py
class DocumentProcessor:
    def __init__(self):
        self.pdf_parser = PyPDF2Reader()
        self.docx_parser = DocumentParser()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    async def process_certification_guide(
        self, 
        file_path: str, 
        certification_id: str
    ) -> ProcessingResult:
        """Process uploaded certification materials"""
        
        # Extract text based on file type
        if file_path.endswith('.pdf'):
            text = await self._extract_pdf_text(file_path)
        elif file_path.endswith('.docx'):
            text = await self._extract_docx_text(file_path)
        else:
            raise UnsupportedFileTypeError(f"Unsupported file type: {file_path}")
        
        # Split into semantic chunks
        chunks = self.text_splitter.split_text(text)
        
        # Generate metadata for each chunk
        metadata = [
            {
                "certification_id": certification_id,
                "chunk_index": i,
                "source_file": file_path,
                "created_at": datetime.now().isoformat()
            }
            for i, chunk in enumerate(chunks)
        ]
        
        return ProcessingResult(chunks=chunks, metadata=metadata)
```

#### Deliverables
- [ ] ChromaDB vector database operational
- [ ] Document processing pipeline handling PDF/DOCX/TXT
- [ ] Basic certification profile CRUD operations
- [ ] Unit tests for core knowledge base functions

#### Success Criteria
- Document ingestion processing 100 pages in <1 minute
- Vector search returning results in <500ms
- 95% successful document processing rate

### Week 2: Workflow Orchestration Core

#### Objectives
- Implement workflow state machine
- Create PostgreSQL schema for state tracking
- Build basic step execution framework

#### Technical Tasks

**Day 1-2: Database Schema Implementation**
```sql
-- database/migrations/001_initial_schema.sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    certification_profile_id UUID,
    current_step VARCHAR(50) NOT NULL,
    execution_status VARCHAR(50) NOT NULL DEFAULT 'initiated',
    
    -- Step tracking
    step_execution_log JSONB DEFAULT '[]',
    error_log JSONB DEFAULT '[]',
    
    -- Google resources
    google_form_id VARCHAR(255),
    google_sheet_id VARCHAR(255),
    google_drive_folder_id VARCHAR(255),
    
    -- Workflow data
    assessment_data JSONB,
    gap_analysis_results JSONB,
    training_plan JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    estimated_completion_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_workflow_status ON workflow_executions(execution_status);
CREATE INDEX idx_workflow_user ON workflow_executions(user_id);
```

**Day 3-4: Workflow State Machine**
```python
# src/workflow/orchestrator.py
class WorkflowOrchestrator:
    def __init__(self):
        self.state_manager = WorkflowStateManager()
        self.step_registry = WorkflowStepRegistry()
        self.notification_service = NotificationService()
    
    async def initiate_assessment_workflow(
        self, 
        request: AssessmentRequest
    ) -> WorkflowExecution:
        """Initiate new assessment workflow"""
        
        # Create workflow state
        workflow_id = await self.state_manager.create_workflow(
            user_id=request.user_id,
            certification_profile_id=request.certification_id,
            initial_step=WorkflowStep.ASSESSMENT_GENERATION
        )
        