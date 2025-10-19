# RAG Resource Loading Trace - Certification Profile → Resources Tab

## Complete Flow Diagram

```
USER CLICKS: Certification Profile → Resources Tab
  ↓
[EnhancedCertificationProfileForm.tsx:778]
  TabsContent value="resources"
  ↓
[EnhancedCertificationProfileForm.tsx:780]
  <ResourceManager
    certProfileId={profile.id}
    onResourceDeleted={...}
    onResourcesChanged={...}
  />
  ↓
[ResourceManager.tsx:206] useEffect runs on mount
  ↓
[ResourceManager.tsx:100] loadResources()
  ↓
[ResourceManager.tsx:103]
  fetch(`/api/presgen-assess/files/profile?profileId=${certProfileId}`)
  ↓
NEXT.JS API ROUTE
[presgen-ui/src/app/api/presgen-assess/files/profile/route.ts:11-13]
  Extract profileId from query params
  ↓
[route.ts:21-22]
  Construct backend URL:
  http://localhost:8000/api/v1/presgen-assess/files/profile/${profileId}
  ↓
[route.ts:26-31]
  Proxy request to backend
  ↓
BACKEND FASTAPI
[presgen-assess on port 8000]
  ↓
[src/service/app.py:177]
  app.include_router(api_router, prefix="/api/v1")
  ↓
[src/service/api/v1/router.py:117-121]
  api_router.include_router(
    file_management.router,
    prefix="/presgen-assess"
  )
  ↓
[src/service/api/v1/endpoints/file_management.py:24]
  router = APIRouter(prefix="/files")
  ↓
[file_management.py:200-212]
  @router.get("/profile/{cert_profile_id}")
  async def list_files_for_profile(cert_profile_id: str)
  ↓
[file_management.py:207]
  files = file_registry.get_files_for_profile(cert_profile_id)
  ↓
[src/service/file_upload_service.py:459-473]
  FileRegistry.get_files_for_profile()
    - Calls _load_from_database()
    - Loads from knowledge_base_documents table
    - Returns List[FileMetadata]
  ↓
[file_upload_service.py:438-457]
  _load_from_database()
    - Queries knowledge_base_documents table
    - Filters by certification_profile_id
    - Converts DB records to FileMetadata objects
  ↓
DATABASE QUERY
[file_upload_service.py:443-447]
  SELECT * FROM knowledge_base_documents
  WHERE certification_profile_id = '455dae60-065c-4038-b3df-6d769b955dbb'
  ↓
RETURNS 4 FILES
  ↓
RESPONSE FLOWS BACK UP THE STACK
  ↓
[file_management.py:209-212]
  return FileListResponse(files=files, total_count=len(files))
  ↓
[route.ts:37-40]
  if (backendResponse && backendResponse.ok)
    return NextResponse.json(responseData)
  ↓
[ResourceManager.tsx:109-110]
  const data = await response.json()
  setResources(data.files || [])
  ↓
REACT RE-RENDERS
  ↓
[ResourceManager.tsx:327-420]
  Renders each file resource as a Card with:
    - Filename
    - Resource type badge
    - File size
    - Upload timestamp
    - Processing status
    - Download/Delete buttons
```

## Key Components

### 1. UI Component: ResourceManager

**Location**: `presgen-ui/src/components/file-upload/ResourceManager.tsx`

**Purpose**: Displays and manages RAG resources for a certification profile

**Key Methods**:
- `loadResources()` - Fetches files from API (line 100)
- `handleRefresh()` - Manual refresh button handler (line 120)
- `handleDelete()` - Delete file handler (line 126)
- `handleDownload()` - Download file handler (line 146)

**API Endpoint Called**:
```typescript
fetch(`/api/presgen-assess/files/profile?profileId=${certProfileId}`)
```

**State Management**:
- `resources: FileResource[]` - Array of loaded files
- `loading: boolean` - Loading state
- `error: string | null` - Error messages
- `filterType, filterStatus, searchTerm` - Filter states

### 2. Next.js API Route Proxy

**Location**: `presgen-ui/src/app/api/presgen-assess/files/profile/route.ts`

**Purpose**: Proxies requests from UI to backend API

**Flow**:
1. Extracts `profileId` from query params
2. Constructs backend URL (port 8000)
3. Forwards request to backend
4. Returns response or falls back to mock storage

**Backend URL Construction**:
```typescript
const backendUrl = `${process.env.PRESGEN_ASSESS_URL || 'http://localhost:8000'}/api/v1/presgen-assess/files/profile/${profileId}`;
```

### 3. Backend API Endpoint

**Location**: `presgen-assess/src/service/api/v1/endpoints/file_management.py`

**Route Registration Path**:
```
/api/v1                    ← App prefix (settings.api_v1_prefix)
  /presgen-assess          ← Router prefix (from router.py:119)
    /files                 ← APIRouter prefix (file_management.py:24)
      /profile/{id}        ← Endpoint path (file_management.py:200)

Full path: /api/v1/presgen-assess/files/profile/{cert_profile_id}
```

**Endpoint Implementation** (lines 200-212):
```python
@router.get("/profile/{cert_profile_id}", response_model=FileListResponse)
async def list_files_for_profile(cert_profile_id: str):
    """List all files for a certification profile"""

    # Get files from registry (loads from database)
    files = file_registry.get_files_for_profile(cert_profile_id)

    return FileListResponse(
        files=files,
        total_count=len(files)
    )
```

### 4. FileRegistry (Database-Backed)

**Location**: `presgen-assess/src/service/file_upload_service.py`

**Key Change**: Now persists to database instead of in-memory only

**Methods**:

#### `get_files_for_profile()` (lines 459-473)
```python
def get_files_for_profile(self, cert_profile_id: str) -> List[FileMetadata]:
    """Get all files for a certification profile - loads from database"""

    # Load from database to ensure we have latest data
    file_metadatas = self._load_from_database(cert_profile_id=cert_profile_id)

    # Update cache
    for fm in file_metadatas:
        self._files[fm.file_id] = fm

    return file_metadatas
```

#### `_load_from_database()` (lines 438-457)
```python
def _load_from_database(self, cert_profile_id: str = None, user_id: str = None) -> List[FileMetadata]:
    """Load file metadata from database"""
    from src.models.certification import KnowledgeBaseDocument
    from uuid import UUID

    db = self._get_db()
    query = db.query(KnowledgeBaseDocument)

    if cert_profile_id:
        # Convert string UUID to UUID object if needed
        profile_uuid = UUID(cert_profile_id) if isinstance(cert_profile_id, str) else cert_profile_id
        query = query.filter_by(certification_profile_id=profile_uuid)

    documents = query.all()

    # Convert database records to FileMetadata objects
    file_metadatas = []
    for doc in documents:
        file_metadata = FileMetadata(
            file_id=str(doc.id),
            original_filename=doc.original_filename,
            # ... other fields
        )
        file_metadatas.append(file_metadata)

    return file_metadatas
```

### 5. Database Table

**Table**: `knowledge_base_documents`

**Schema** (from `src/models/certification.py:48-66`):
```python
class KnowledgeBaseDocument(Base):
    __tablename__ = "knowledge_base_documents"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    certification_profile_id = Column(PGUUID(as_uuid=True), nullable=False)
    original_filename = Column(String(500), nullable=False)
    stored_path = Column(Text, nullable=False)
    document_type = Column(String(50))  # MIME type
    content_classification = Column(String(50))  # exam_guide, transcript, supplemental
    file_size_bytes = Column(Integer, nullable=False)
    processing_status = Column(String(50), default='pending')
    chunk_count = Column(Integer)
    checksum = Column(String(64))
    created_at = Column(DateTime)
```

**Current Data**:
```sql
SELECT * FROM knowledge_base_documents
WHERE certification_profile_id = '455dae60-065c-4038-b3df-6d769b955dbb';

-- Returns 4 rows:
-- 1. aws-ml-specialty-exam-guide.txt (exam_guide, 5,406 bytes)
-- 2. aws-ml-specialty-exam-guide.md (exam_guide, 5,406 bytes)
-- 3. ml-course-transcript.txt (transcript, 6,194 bytes)
-- 4. ml-course-transcript.md (transcript, 6,194 bytes)
```

## UI Rendering

### ResourceManager Display (lines 327-420)

Each file is rendered as a Card showing:

1. **Header**:
   - File icon
   - Original filename
   - Resource type badge (color-coded)

2. **Metadata**:
   - File size (formatted)
   - Upload timestamp
   - Chunk count (if processed)

3. **Status**:
   - Status icon (checkmark, clock, alert)
   - Status text (completed, processing, pending, failed)
   - Error message (if failed)

4. **Actions**:
   - Download button
   - Delete button (with confirmation dialog)

### Stats Display (lines 246-269)

Quick stats badges showing:
- Total files
- Exam Guides count
- Transcripts count
- Supplemental count
- Processed count
- Processing count (if any)
- Failed count (if any)

## Refresh Flow

When user clicks "Refresh" button:

1. `handleRefresh()` called (line 120)
2. Sets `refreshing` state to true
3. Calls `loadResources()`
4. Fetches fresh data from API
5. Updates `resources` state
6. Triggers `onResourcesChanged()` callback
7. React re-renders with new data

## Error Handling

### UI Level (ResourceManager.tsx)
- Try-catch in `loadResources()` (lines 101-117)
- Displays error message in red banner (lines 310-315)
- Falls back to empty list on error

### API Route Level (route.ts)
- Try-catch around backend fetch (lines 24-34)
- Falls back to mock storage if backend unavailable (lines 43-69)
- Returns empty list with error message (lines 72-82)

### Backend Level (file_management.py)
- FileRegistry handles database errors gracefully
- Returns empty list if query fails
- Logs errors for debugging

## Integration Points

### Where ResourceManager is Used:

**EnhancedCertificationProfileForm.tsx** (line 780):
```tsx
<TabsContent value="resources">
  {profile?.id ? (
    <ResourceManager
      certProfileId={profile.id}
      onResourceDeleted={handleResourceDeleted}
      onResourcesChanged={() => setResourceCount(prev => prev)}
    />
  ) : (
    <Card>
      <CardContent>
        Save the certification profile first to manage resources
      </CardContent>
    </Card>
  )}
</TabsContent>
```

**Conditions**:
- Only renders if `profile.id` exists
- User must save profile before accessing Resources tab

## Testing the Complete Flow

### 1. Test Backend Endpoint Directly:
```bash
curl http://localhost:8000/api/v1/presgen-assess/files/profile/455dae60-065c-4038-b3df-6d769b955dbb
```

**Expected Response**:
```json
{
  "files": [
    {
      "file_id": "...",
      "original_filename": "aws-ml-specialty-exam-guide.txt",
      "resource_type": "exam_guide",
      ...
    },
    ...
  ],
  "total_count": 4
}
```

### 2. Test UI Proxy Route:
```bash
curl "http://localhost:3000/api/presgen-assess/files/profile?profileId=455dae60-065c-4038-b3df-6d769b955dbb"
```

### 3. Test in Browser:
1. Navigate to http://localhost:3000
2. Go to Certification Profiles
3. Select "AWS Machine Learning Specialty"
4. Click "Resources" tab
5. Should see 4 files displayed

## Summary

The RAG resources loading flow is now **fully functional**:

✅ Database persistence implemented
✅ FileRegistry loads from database
✅ API endpoint registered and working
✅ UI proxy route configured correctly
✅ ResourceManager component renders files
✅ Refresh functionality works
✅ Error handling in place

**All 4 files** for AWS Machine Learning Specialty should now appear in the UI!
