# ChromaDB Collection and Metadata Schema Design

## Overview

This document defines the ChromaDB collection structure and metadata schema for the PresGen-Assess certification profile system. The design ensures strict tenant isolation, version control, and efficient retrieval of certification-specific resources.

## Collection Naming Convention

### Primary Collection Pattern
```python
collection_name = f"assess_{user_id}_{cert_id}_{bundle_version}"

# Examples:
# assess_user123_aws-saa-c03_v1.0
# assess_user456_azure-az900_v2.1
# assess_company789_cissp_v1.5
```

### Collection Metadata
Each collection maintains metadata for validation and consistency:

```python
collection_metadata = {
    "cert_id": cert_id,                    # e.g., "aws-saa-c03"
    "cert_name": cert_name,                # e.g., "AWS Solutions Architect Associate"
    "bundle_version": bundle_version,       # e.g., "v1.0"
    "embed_model": "text-embedding-3-small",  # Embedding model used
    "created_at": "2025-09-24T08:00:00Z",
    "user_id": user_id,
    "tenant_isolation": True,
    "resource_types": ["exam_guide", "transcript"]
}
```

## Document Metadata Schema

### Core Metadata Structure
Every document chunk includes the following metadata:

```python
document_metadata = {
    # Tenant & Certification Isolation
    "user_id": str,                    # e.g., "user123"
    "cert_id": str,                    # e.g., "aws-saa-c03"
    "cert_profile_id": str,            # UUID of certification profile
    "bundle_version": str,             # e.g., "v1.0"

    # Resource Classification
    "resource_type": str,              # "exam_guide" | "transcript" | "supplemental"
    "source_file": str,                # Original filename
    "source_uri": str,                 # File path or URL
    "mime_type": str,                  # "application/pdf" | "text/plain" | "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    # Content Structure
    "section": str,                    # Section title or chapter name
    "page": int,                       # Page number (if applicable)
    "chunk_index": int,                # Sequential chunk number
    "chunk_size": int,                 # Character count of chunk

    # Content Classification
    "content_type": str,               # "concept" | "example" | "procedure" | "assessment"
    "domain": str,                     # Certification domain (from exam_domains)
    "subdomain": str,                  # Specific subdomain or skill area
    "difficulty_level": str,           # "beginner" | "intermediate" | "advanced" | "expert"

    # Technical Metadata
    "embed_model": str,                # "text-embedding-3-small"
    "processing_timestamp": str,       # ISO 8601 timestamp
    "content_hash": str,               # SHA-256 hash of content
    "language": str,                   # "en" | "es" | etc.

    # Retrieval Optimization
    "keywords": List[str],             # Extracted keywords for filtering
    "concepts": List[str],             # Key concepts covered
    "relevance_score": float,          # Content relevance score (0.0-1.0)

    # Version Control
    "file_version": str,               # Version of source file
    "chunk_version": str,              # Version of chunk processing
    "schema_version": str              # Metadata schema version
}
```

## Resource Type Specifications

### 1. Exam Guide Resources
```python
exam_guide_metadata = {
    **document_metadata,
    "resource_type": "exam_guide",
    "exam_code": str,                  # e.g., "SAA-C03"
    "official_source": bool,           # True if from official provider
    "content_authority": str,          # "AWS" | "Microsoft" | "CompTIA" etc.
    "exam_objectives": List[str],      # Related exam objectives
    "study_weight": float,             # Importance weight (0.0-1.0)
}
```

### 2. Transcript Resources
```python
transcript_metadata = {
    **document_metadata,
    "resource_type": "transcript",
    "course_title": str,               # Course or video title
    "instructor": str,                 # Instructor name
    "duration_minutes": int,           # Content duration
    "transcript_quality": str,         # "high" | "medium" | "low"
    "speaker_context": str,            # "instructor" | "student" | "mixed"
}
```

### 3. Supplemental Resources
```python
supplemental_metadata = {
    **document_metadata,
    "resource_type": "supplemental",
    "material_type": str,              # "whitepaper" | "blog" | "documentation"
    "author": str,                     # Author or organization
    "publication_date": str,           # Publication date
    "credibility_score": float,        # Source credibility (0.0-1.0)
}
```

## Isolation and Security

### Tenant Isolation Strategy
1. **Collection-based isolation**: Each user/cert combination gets its own collection
2. **Metadata filtering**: All queries include user_id and cert_id filters
3. **API enforcement**: Application layer enforces access controls
4. **No cross-tenant access**: Collections cannot see each other's data

### Query Filters
```python
# Required filters for all queries
mandatory_filters = {
    "user_id": current_user_id,
    "cert_id": selected_cert_id,
    "bundle_version": active_bundle_version
}

# Optional filters for refinement
optional_filters = {
    "resource_type": "exam_guide",
    "domain": "Design Secure Architectures",
    "difficulty_level": "intermediate",
    "content_type": "concept"
}
```

## Versioning Strategy

### Bundle Versioning
- **Immutable bundles**: Each version is read-only once created
- **Version progression**: v1.0 → v1.1 → v2.0 for updates
- **Rollback capability**: Can revert to previous bundle versions
- **Parallel versions**: Multiple versions can coexist

### Version Lifecycle
```python
def create_new_bundle_version(cert_profile_id, files):
    """Create new immutable bundle version"""
    current_version = get_latest_bundle_version(cert_profile_id)
    new_version = increment_version(current_version)

    # Create new collection
    collection_name = f"assess_{user_id}_{cert_id}_{new_version}"

    # Process and store all files
    for file in files:
        chunks = process_file(file)
        store_chunks_with_metadata(collection_name, chunks, new_version)

    # Update certification profile
    update_certification_profile(cert_profile_id, {
        "bundle_version": new_version,
        "knowledge_base_path": collection_name
    })
```

## Retrieval Patterns

### 1. Assessment Question Generation
```python
def retrieve_for_assessment(user_id, cert_id, domain, difficulty):
    filters = {
        "user_id": user_id,
        "cert_id": cert_id,
        "resource_type": "exam_guide",
        "domain": domain,
        "difficulty_level": difficulty,
        "content_type": ["concept", "procedure"]
    }
    return collection.query(query_texts=context, where=filters, n_results=10)
```

### 2. Gap Analysis Context
```python
def retrieve_for_gap_analysis(user_id, cert_id, weak_domains):
    filters = {
        "user_id": user_id,
        "cert_id": cert_id,
        "domain": {"$in": weak_domains},
        "content_type": ["concept", "example"]
    }
    return collection.query(query_texts=knowledge_gaps, where=filters, n_results=20)
```

### 3. Presentation Generation
```python
def retrieve_for_presentation(user_id, cert_id, topics, audience_level):
    filters = {
        "user_id": user_id,
        "cert_id": cert_id,
        "concepts": {"$in": topics},
        "difficulty_level": audience_level,
        "resource_type": ["exam_guide", "transcript"]
    }
    return collection.query(query_texts=topics, where=filters, n_results=15)
```

## Performance Optimization

### Indexing Strategy
- **Primary indices**: user_id, cert_id, bundle_version
- **Secondary indices**: resource_type, domain, content_type
- **Composite indices**: (user_id, cert_id, resource_type)

### Caching Strategy
- **Collection metadata**: Cached for 1 hour
- **Frequent queries**: Cached for 15 minutes
- **Embedding results**: Cached by content hash

### Query Optimization
- **Batch processing**: Group similar queries
- **Result limits**: Reasonable n_results limits (5-20)
- **Filter first**: Apply metadata filters before similarity search

## Monitoring and Maintenance

### Health Checks
- Collection existence and accessibility
- Metadata schema compliance
- Embedding model consistency
- Query performance metrics

### Cleanup Operations
- **Orphaned collections**: Remove collections for deleted profiles
- **Version cleanup**: Remove old bundle versions (keep last 3)
- **Temp collections**: Clean up failed upload collections

### Audit Trail
- Document ingestion logs
- Query access logs
- Version change history
- User access patterns

## Implementation Checklist

- [ ] ChromaDB client with collection management
- [ ] Metadata validation schemas
- [ ] Document processing pipeline
- [ ] Query interface with filtering
- [ ] Version management system
- [ ] Cleanup and maintenance jobs
- [ ] Monitoring and health checks
- [ ] Security validation tests

---

**Schema Version**: 1.0
**Last Updated**: September 24, 2025
**Maintainer**: PresGen-Assess Team