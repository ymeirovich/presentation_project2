# Data Model: Read Specification Document

## Entity Definitions

### Document Entity
Represents a specification document available for reading.

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum

class DocumentType(Enum):
    SPECIFICATION = "specification"
    ARCHITECTURE = "architecture"
    IMPLEMENTATION_PLAN = "implementation_plan"

@dataclass
class Document:
    """Core document entity with metadata and content"""
    name: str
    document_type: DocumentType
    file_path: Path
    content: Optional[str] = None
    file_size_bytes: int = 0
    last_modified: Optional[datetime] = None
    checksum: Optional[str] = None
    encoding: str = "utf-8"

    def is_valid(self) -> bool:
        """Validate document exists and is readable"""
        return (
            self.file_path.exists()
            and self.file_path.is_file()
            and self.file_path.suffix.lower() in ['.md', '.txt']
        )

    def get_size_mb(self) -> float:
        """Get file size in megabytes"""
        return self.file_size_bytes / (1024 * 1024)
```

### Document Access Request
Represents a request to access a document with user context.

```python
@dataclass
class DocumentAccessRequest:
    """Request to access a specific document"""
    document_name: str
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    request_timestamp: datetime = datetime.now()
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None

    def to_audit_log(self) -> dict:
        """Convert request to audit log format"""
        return {
            "document_name": self.document_name,
            "user_id": self.user_id,
            "user_role": self.user_role,
            "timestamp": self.request_timestamp.isoformat(),
            "client_ip": self.client_ip,
            "user_agent": self.user_agent
        }
```

### Document Access Response
Represents the response for a document access request.

```python
class AccessStatus(Enum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    ACCESS_DENIED = "access_denied"
    TOO_LARGE = "too_large"
    CORRUPTED = "corrupted"
    SERVER_ERROR = "server_error"

@dataclass
class DocumentAccessResponse:
    """Response for document access request"""
    status: AccessStatus
    document: Optional[Document] = None
    content: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    suggestions: Optional[list[str]] = None
    response_timestamp: datetime = datetime.now()

    def to_http_response(self) -> tuple[int, dict]:
        """Convert to HTTP status code and response body"""
        status_map = {
            AccessStatus.SUCCESS: 200,
            AccessStatus.NOT_FOUND: 404,
            AccessStatus.ACCESS_DENIED: 403,
            AccessStatus.TOO_LARGE: 413,
            AccessStatus.CORRUPTED: 422,
            AccessStatus.SERVER_ERROR: 500
        }

        response_body = {
            "status": self.status.value,
            "timestamp": self.response_timestamp.isoformat()
        }

        if self.status == AccessStatus.SUCCESS and self.content:
            response_body["content"] = self.content
            if self.document:
                response_body["metadata"] = {
                    "name": self.document.name,
                    "type": self.document.document_type.value,
                    "size_bytes": self.document.file_size_bytes,
                    "last_modified": self.document.last_modified.isoformat() if self.document.last_modified else None
                }
        else:
            response_body["error"] = {
                "message": self.error_message,
                "code": self.error_code,
                "suggestions": self.suggestions or []
            }

        return status_map[self.status], response_body
```

### User Session
Represents user context for document access control.

```python
@dataclass
class UserSession:
    """User session information for access control"""
    user_id: Optional[str] = None
    role: Optional[str] = None
    permissions: list[str] = None
    session_start: datetime = datetime.now()
    is_authenticated: bool = False

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions or self.role == "admin"

    def can_access_document(self, document_type: DocumentType) -> bool:
        """Check if user can access specific document type"""
        public_documents = [DocumentType.SPECIFICATION, DocumentType.ARCHITECTURE]

        if document_type in public_documents:
            return True

        if document_type == DocumentType.IMPLEMENTATION_PLAN:
            return self.is_authenticated

        return False
```

### Access Audit Log
Tracks document access for security and analytics.

```python
@dataclass
class AccessAuditLog:
    """Audit log entry for document access"""
    log_id: str
    document_name: str
    user_id: Optional[str]
    access_granted: bool
    status: AccessStatus
    timestamp: datetime
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    error_details: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "log_id": self.log_id,
            "document_name": self.document_name,
            "user_id": self.user_id,
            "access_granted": self.access_granted,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "error_details": self.error_details
        }
```

## Entity Relationships

```
UserSession (1) -----> (0..n) DocumentAccessRequest
    |                        |
    |                        |
    v                        v
AccessAuditLog (n) <----- (1) DocumentAccessResponse
    |                        |
    |                        |
    v                        v
Document (1) <------------- (1) DocumentAccessRequest
```

## Validation Rules

### Document Validation
- Document name must be alphanumeric with hyphens/underscores only
- File path must exist and be readable
- File size must not exceed 10MB
- File must have .md or .txt extension
- Content must be valid UTF-8

### Access Request Validation
- Document name is required and non-empty
- User ID format validation (if provided)
- Timestamp must be recent (within 5 minutes)

### Response Validation
- Status must be valid AccessStatus enum value
- Content is required for successful responses
- Error message is required for failed responses
- Timestamps must be in ISO format

## State Transitions

### Document Access Flow
```
Initial Request → Validation → Permission Check → File Access → Response Generation
     |              |              |               |              |
     v              v              v               v              v
   Valid?     → Authorized? → Exists/Readable? → Success → Audit Log
     |              |              |               |
     |              |              |               |
   Invalid    Unauthorized    Not Found/Error   Failure
     |              |              |               |
     v              v              v               v
Error Response  Access Denied   Error Response  Error Response
     |              |              |               |
     v              v              v               v
  Audit Log     Audit Log     Audit Log       Audit Log
```

## Performance Considerations

### Caching Strategy
- Document metadata cached for 1 hour
- Document content cached for 30 minutes
- Cache invalidation on file modification
- User permissions cached per session

### Database Indexing
- Index on document_name for fast lookup
- Index on timestamp for audit log queries
- Index on user_id for access tracking