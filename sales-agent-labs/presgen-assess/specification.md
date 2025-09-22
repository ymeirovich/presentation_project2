# PresGen-Assess Technical Specification

## System Overview

PresGen-Assess is an adaptive learning assessment module that integrates with the existing PresGen ecosystem to provide diagnostic gap analysis and automated remediation content generation for professional certification preparation. The system features async workflow support, RAG-enhanced content generation, and support for up to 40-slide presentations.

## Directory Structure

```
presgen-assess/
├── src/
│   ├── assessment/
│   │   ├── __init__.py
│   │   ├── generator.py          # RAG-enhanced assessment generation
│   │   ├── analyzer.py           # Multi-dimensional gap analysis
│   │   ├── validator.py          # Assessment quality assurance
│   │   └── templates/            # RAG-enhanced prompt templates
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── base.py              # Dual-stream RAG implementation
│   │   ├── certifications.py    # Certification profile management
│   │   ├── documents.py         # Document processing with content classification
│   │   └── embeddings.py        # Vector embeddings with source attribution
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── google_forms.py      # Forms API integration
│   │   ├── google_sheets.py     # Sheets API integration
│   │   ├── google_drive.py      # Drive API integration
│   │   ├── presgen_core.py      # Core module integration (40-slide support)
│   │   └── presgen_avatar.py    # Avatar module integration
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # Async-aware workflow orchestration
│   │   ├── steps.py             # Individual workflow steps with RAG context
│   │   └── notifications.py     # Process notifications
│   └── models/
│       ├── __init__.py
│       ├── assessment.py        # Assessment data models (40-slide validation)
│       ├── gaps.py             # Gap analysis models
│       ├── certification.py    # Certification profile models
│       └── workflow.py         # Async workflow state models
├── frontend/
│   ├── components/
│   │   ├── SlideSelector.jsx    # 1-40 slide range selector
│   │   ├── WorkflowResume.jsx   # Sheet URL input component
│   │   └── AdminDashboard.jsx   # Knowledge base CRUD interface
│   ├── pages/
│   └── utils/
├── knowledge-base/
│   ├── certifications/
│   │   ├── aws/
│   │   │   ├── exam_guides/      # Official AWS certification materials
│   │   │   └── transcripts/      # Curated course transcripts
│   │   ├── azure/
│   │   └── gcp/
│   ├── documents/              # Raw uploaded materials
│   └── embeddings/            # ChromaDB vector storage
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── config/
│   ├── certifications.yaml    # Certification profiles
│   ├── prompts.yaml           # Static prompt templates
│   └── rag_config.yaml        # RAG system configuration
└── docs/
    ├── api.md
    ├── workflow.md
    └── knowledge_base.md
```

## Workflow Architecture

### Complete Assessment Workflow Process (Async-Aware)

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 1. Request      │    │ 2. Generate     │    │ 3. Deploy       │
│ Assessment      │───▶│ Assessment      │───▶│ Google Forms    │
│                 │    │ (RAG Enhanced)  │    │ + Drive         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 4. Return URLs  │    │ 5. ASYNC BREAK  │    │ 6. Resume with  │
│ to User         │───▶│ User Closes     │───▶│ Sheet URL Input │
│                 │    │ Application     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 7. Process      │    │ 8. Generate     │    │ 9. Create       │
│ Assessment      │───▶│ Training Plan   │───▶│ Course Outlines │
│ Results         │    │ (RAG Context)   │    │ (RAG Sources)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 10. PresGen-Core│    │ 11. PresGen-    │    │ 12. Finalize    │
│ Presentations   │───▶│ Avatar Videos   │───▶│ Public Resources│
│ (1-40 slides)   │    │ Generation      │    │ & Access Links  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### RAG Enhancement Requirements
- **Assessment Generation**: Must incorporate both exam guides AND course transcripts
- **Course Content**: Generated presentations must reference specific RAG sources
- **Source Attribution**: All generated content includes citations to knowledge base materials

## RAG Knowledge Base Architecture

### Vector Database Implementation

```python
# RAG Knowledge Base Components
class RAGKnowledgeBase:
    def __init__(self):
        self.vector_store = ChromaDB()  # Vector database
        self.embeddings_model = OpenAIEmbeddings()
        self.document_processor = DocumentProcessor()
        self.retriever = DocumentRetriever()
    
    def ingest_documents(self, certification_type: str, documents: List[str]):
        """Process and embed certification materials"""
        for doc_path in documents:
            # Process document (PDF/DOCX/TXT)
            chunks = self.document_processor.chunk_document(doc_path)
            
            # Generate embeddings
            embeddings = self.embeddings_model.embed_documents(chunks)
            
            # Store in vector database with metadata
            self.vector_store.add_documents(
                documents=chunks,
                embeddings=embeddings,
                metadatas=[{
                    'certification': certification_type,
                    'document': doc_path,
                    'chunk_id': i
                } for i in range(len(chunks))]
            )
    
    def retrieve_context(self, query: str, certification: str, k: int = 5):
        """Retrieve relevant context for assessment generation"""
        results = self.vector_store.similarity_search(
            query=query,
            filter={'certification': certification},
            k=k
        )
        return [doc.page_content for doc in results]
```

### Document Processing Pipeline

```python
class DocumentProcessor:
    def __init__(self):
        self.pdf_parser = PyPDFLoader()
        self.docx_parser = UnstructuredWordDocumentLoader()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def chunk_document(self, document_path: str) -> List[str]:
        """Process and chunk documents for RAG ingestion"""
        
        # Determine document type and parse
        if document_path.endswith('.pdf'):
            documents = self.pdf_parser.load(document_path)
        elif document_path.endswith('.docx'):
            documents = self.docx_parser.load(document_path)
        elif document_path.endswith('.txt'):
            with open(document_path, 'r') as f:
                documents = [Document(page_content=f.read())]
        
        # Split into chunks
        chunks = self.text_splitter.split_documents(documents)
        return [chunk.page_content for chunk in chunks]
```

## Certification Profile Management

### CRUD Operations for Certification Profiles

```python
class CertificationProfileManager:
    def create_certification_profile(self, profile_data: CertificationProfileCreate):
        """Create new certification profile"""
        profile = CertificationProfile(
            name=profile_data.name,
            version=profile_data.version,
            exam_domains=profile_data.domains,
            knowledge_base_id=self._create_knowledge_base(profile_data.name),
            created_at=datetime.now()
        )
        
        # Store in database
        return self.db.create_certification_profile(profile)
    
    def upload_certification_materials(self, profile_id: str, files: List[UploadFile]):
        """Upload and process certification materials"""
        profile = self.get_profile(profile_id)
        
        for file in files:
            # Save file to knowledge-base directory
            file_path = f"knowledge-base/certifications/{profile.name}/{file.filename}"
            self._save_uploaded_file(file, file_path)
            
            # Process for RAG ingestion
            self.rag_knowledge_base.ingest_documents(profile.name, [file_path])
        
        # Update profile with new documents
        self._update_profile_documents(profile_id, [file.filename for file in files])
    
    def update_certification_profile(self, profile_id: str, updates: dict):
        """Update certification profile"""
        return self.db.update_certification_profile(profile_id, updates)
    
    def delete_certification_profile(self, profile_id: str):
        """Delete certification profile and associated resources"""
        profile = self.get_profile(profile_id)
        
        # Remove knowledge base documents
        self.rag_knowledge_base.delete_documents(profile.name)
        
        # Remove from database
        self.db.delete_certification_profile(profile_id)
```

### Certification Profile Data Model

```python
@dataclass
class CertificationProfile:
    id: str
    name: str  # e.g., "AWS Solutions Architect Associate"
    version: str  # e.g., "SAA-C03"
    exam_domains: List[ExamDomain]
    knowledge_base_documents: List[str]
    assessment_template: dict
    created_at: datetime
    updated_at: datetime

@dataclass
class ExamDomain:
    name: str
    weight_percentage: int
    subdomains: List[str]
    skills_measured: List[str]
```

## Workflow Orchestration

### Main Workflow Orchestrator

```python
class AssessmentWorkflowOrchestrator:
    def __init__(self):
        self.google_forms = GoogleFormsIntegration()
        self.google_sheets = GoogleSheetsIntegration()
        self.google_drive = GoogleDriveIntegration()
        self.assessment_generator = AssessmentGenerator()
        self.gap_analyzer = GapAnalyzer()
        self.content_pipeline = ContentGenerationPipeline()
        self.notification_service = NotificationService()
    
    async def execute_full_workflow(self, assessment_request: AssessmentRequest):
        """Execute complete assessment workflow"""
        
        # Step 1: Request Assessment
        workflow_state = self._initialize_workflow(assessment_request)
        
        # Step 2: Generate Assessment using RAG + Multi-dimensional Analysis
        assessment = await self._generate_assessment(workflow_state)
        
        # Step 3: Create Google Resources with Public Access
        google_resources = await self._create_google_resources(assessment, workflow_state)
        
        # Step 4: Wait for Human Completion (Asynchronous)
        await self._setup_completion_monitoring(workflow_state, google_resources)
        
        return {
            "workflow_id": workflow_state.id,
            "google_form_url": google_resources.form_url,
            "google_drive_folder": google_resources.drive_folder_url,
            "status": "awaiting_completion"
        }
    
    async def process_completion(self, sheet_url: str, workflow_id: str):
        """Process assessment completion (Human-in-the-loop)"""
        
        # Step 5: Retrieve and Analyze Results
        results = await self.google_sheets.retrieve_results(sheet_url)
        gap_analysis = await self.gap_analyzer.analyze_gaps(results)
        
        # Step 6: Output Gap Analysis to New Sheet Tab
        await self.google_sheets.create_tab_with_data(
            sheet_url, "Gap_Analysis", gap_analysis
        )
        
        # Step 7: Generate Training Plan
        training_plan = await self._generate_training_plan(gap_analysis)
        await self.google_sheets.create_tab_with_data(
            sheet_url, "Training_Plan", training_plan
        )
        
        # Step 8: Generate Course Outlines using RAG
        course_outlines = await self._generate_course_outlines(training_plan)
        for i, outline in enumerate(course_outlines):
            await self.google_sheets.create_tab_with_data(
                sheet_url, f"Course_Outline_{i+1}", outline
            )
        
        # Step 9: Generate PresGen-Core Presentations
        presentations = await self._generate_presentations(course_outlines)
        
        # Step 10: Generate PresGen-Avatar Videos
        avatar_videos = await self._generate_avatar_videos(presentations)
        
        # Step 11: Set Public Permissions and Return Links
        resource_links = await self._finalize_resources(
            presentations, avatar_videos, workflow_id
        )
        
        return resource_links
```

### Google Workspace Integration

```python
class GoogleWorkspaceIntegration:
    def __init__(self):
        self.forms_service = self._initialize_forms_service()
        self.sheets_service = self._initialize_sheets_service()
        self.drive_service = self._initialize_drive_service()
    
    async def create_assessment_resources(self, assessment: Assessment):
        """Create Google Form, Sheet, and Drive folder"""
        
        # Create Drive folder for assessment
        folder = self.drive_service.files().create(
            body={
                'name': f'Assessment_{assessment.id}',
                'mimeType': 'application/vnd.google-apps.folder'
            }
        ).execute()
        
        # Set folder to public
        await self._set_public_permissions(folder['id'])
        
        # Create Google Form
        form = self.forms_service.forms().create(
            body={
                'info': {
                    'title': f'{assessment.certification_type} Assessment',
                    'description': 'Multi-dimensional skills assessment'
                }
            }
        ).execute()
        
        # Create associated Google Sheet
        sheet = self.sheets_service.spreadsheets().create(
            body={
                'properties': {
                    'title': f'Assessment_Results_{assessment.id}'
                }
            }
        ).execute()
        
        # Move to assessment folder
        await self._move_to_folder([form['formId'], sheet['spreadsheetId']], folder['id'])
        
        # Set public permissions
        await self._set_public_permissions(form['formId'])
        await self._set_public_permissions(sheet['spreadsheetId'])
        
        # Link form responses to sheet
        await self._link_form_to_sheet(form['formId'], sheet['spreadsheetId'])
        
        return {
            'form_url': form['responderUri'],
            'sheet_url': f"https://docs.google.com/spreadsheets/d/{sheet['spreadsheetId']}",
            'folder_url': f"https://drive.google.com/drive/folders/{folder['id']}",
            'folder_id': folder['id']
        }
    
    async def _set_public_permissions(self, resource_id: str):
        """Set public access permissions"""
        self.drive_service.permissions().create(
            fileId=resource_id,
            body={
                'role': 'reader',
                'type': 'anyone'
            }
        ).execute()
```

## Data Models

### Workflow State Management

```python
@dataclass
class WorkflowState:
    id: str
    user_id: str
    certification_profile_id: str
    status: WorkflowStatus
    google_form_id: str
    google_sheet_id: str
    google_folder_id: str
    created_at: datetime
    updated_at: datetime
    completion_notified_at: Optional[datetime] = None

class WorkflowStatus(Enum):
    REQUESTED = "requested"
    ASSESSMENT_GENERATED = "assessment_generated"
    AWAITING_COMPLETION = "awaiting_completion"
    COMPLETED = "completed"
    ANALYZING_GAPS = "analyzing_gaps"
    GENERATING_CONTENT = "generating_content"
    FINISHED = "finished"
    ERROR = "error"
```

### Database Schema Updates

```sql
-- Certification profiles
CREATE TABLE certification_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    exam_domains JSONB NOT NULL,
    knowledge_base_documents TEXT[],
    assessment_template JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, version)
);

-- Workflow state tracking
CREATE TABLE workflow_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    certification_profile_id UUID REFERENCES certification_profiles(id),
    status VARCHAR(50) NOT NULL,
    google_form_id VARCHAR(255),
    google_sheet_id VARCHAR(255),
    google_folder_id VARCHAR(255),
    assessment_data JSONB,
    gap_analysis_data JSONB,
    training_plan_data JSONB,
    generated_content JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- RAG document tracking
CREATE TABLE knowledge_base_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    certification_profile_id UUID REFERENCES certification_profiles(id),
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    processed_at TIMESTAMP,
    chunk_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## API Endpoints

### Workflow Management

```python
# Assessment workflow
POST   /assess/request-assessment
POST   /assess/process-completion
GET    /assess/workflow/{workflow_id}/status
POST   /assess/workflow/{workflow_id}/notify-completion

# Certification profile management
GET    /assess/certifications
POST   /assess/certifications
GET    /assess/certifications/{cert_id}
PUT    /assess/certifications/{cert_id}
DELETE /assess/certifications/{cert_id}
POST   /assess/certifications/{cert_id}/upload-materials

# Knowledge base management
POST   /assess/knowledge-base/ingest
GET    /assess/knowledge-base/{cert_id}/documents
DELETE /assess/knowledge-base/{cert_id}/documents/{doc_id}

# Human-in-the-loop processes
POST   /assess/retrieve-sheet-results
POST   /assess/manual-completion-trigger
```

## Integration with PresGen Modules

### PresGen-Core Integration (40-Slide Support)

```python
class PresGenCoreIntegration:
    def __init__(self):
        self.core_api_base = os.getenv('PRESGEN_CORE_URL')
        self.client = httpx.AsyncClient()

    async def generate_presentation(self, course_outline: dict, rag_context: dict):
        """Generate educational presentation with RAG context and 40-slide support"""

        response = await self.client.post(
            f"{self.core_api_base}/presentations/educational",
            json={
                'title': course_outline['title'],
                'content_outline': course_outline['sections'],
                'rag_sources': rag_context['sources'],
                'source_citations': rag_context['citations'],
                'max_slides': 40,  # Support up to 40 slides
                'slide_count': course_outline.get('requested_slides', 20),
                'learning_objectives': course_outline['objectives'],
                'target_audience': 'certification_preparation',
                'difficulty_level': course_outline['difficulty']
            },
            timeout=600  # Extended timeout for larger presentations
        )

        return response.json()

### PresGen-Avatar Integration

```python
class PresGenAvatarIntegration:
    def __init__(self):
        self.avatar_api_base = os.getenv('PRESGEN_AVATAR_URL')
        self.client = httpx.AsyncClient()

    async def generate_avatar_video(self, presentation_data: dict):
        """Generate avatar narration for course presentation (supports 40-slide presentations)"""

        response = await self.client.post(
            f"{self.avatar_api_base}/training/presentation-only",
            json={
                'slides_url': presentation_data['slides_url'],
                'voice_profile': 'instructor',
                'quality_level': 'standard',
                'instructions': 'Create educational narration for certification preparation',
                'max_slides_supported': 40,  # Ensure avatar can handle larger presentations
                'estimated_duration': presentation_data.get('estimated_minutes', 60)
            },
            timeout=900  # Extended timeout for longer presentations
        )

        return response.json()
```

## Performance Requirements

### Workflow Performance Targets
- Assessment generation: <3 minutes (including RAG retrieval)
- Gap analysis processing: <1 minute
- Training plan generation: <30 seconds
- Course outline generation: <2 minutes per course
- Complete workflow: <30 minutes for 5 courses

### RAG System Performance
- Document ingestion: <1 minute per 100 pages
- Context retrieval: <500ms for 5 relevant chunks
- Knowledge base updates: <5 minutes for certification profile
- Vector search accuracy: >85% relevance for assessment generation

## Security and Privacy

### Data Protection
- RAG knowledge base encrypted at rest
- Google API credentials secured in environment variables
- Workflow state data encrypted with user consent
- Public resources clearly marked and consent-based

### Access Control
- User-specific workflow access only
- Certification profile management restricted to admins
- Knowledge base document access logged and audited
- Public resource creation with explicit user approval