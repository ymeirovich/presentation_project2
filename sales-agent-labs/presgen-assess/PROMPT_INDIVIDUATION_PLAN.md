# Prompt Individuation Implementation Plan

## Problem Analysis

### Current Architecture Issues ❌
The current system has **prompt coupling** where:

1. **Knowledge Base and Certification Profile prompts share the same source**
   - Both systems read from `profile.assessment_template._chromadb_prompts`
   - Changes to one affect the other inappropriately
   - No clear separation of concerns

2. **Conflicting Prompt Sources**
   - Database columns: `profile.assessment_prompt`, `profile.presentation_prompt`, `profile.gap_analysis_prompt`
   - Template storage: `profile.assessment_template._chromadb_prompts`
   - Frontend components expect separate prompt systems

3. **Inconsistent Data Flow**
   - Knowledge Base operations modify certification profile prompts
   - Certification Profile modifications affect knowledge base behavior
   - No isolation between different prompt use cases

## Required Separation

### Knowledge Base Prompts (Collection-Level) 🗂️
**Purpose**: Control how knowledge retrieval and ingestion works for a certification's knowledge base
**Scope**: Affects all users of that certification's knowledge base
**Storage**: Should be associated with knowledge base collections, not individual profiles
**Examples**:
- Document ingestion prompts
- Context retrieval prompts
- Semantic search prompts

### Certification Profile Prompts (Profile-Level) 👤
**Purpose**: Control personalized assessment/presentation generation for individual users
**Scope**: Affects only the specific certification profile instance
**Storage**: Database columns in `certification_profiles` table
**Examples**:
- Assessment question generation prompts
- Presentation slide generation prompts
- Gap analysis prompts

## Implementation Plan

### Phase 1: Database Schema Updates 🔧

#### 1.1 Add Knowledge Base Prompt Storage
Create new table for knowledge base-level prompts:

```sql
CREATE TABLE knowledge_base_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_name VARCHAR(255) NOT NULL UNIQUE,
    certification_name VARCHAR(255) NOT NULL,

    -- Knowledge base operation prompts
    document_ingestion_prompt TEXT,
    context_retrieval_prompt TEXT,
    semantic_search_prompt TEXT,
    content_classification_prompt TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    version VARCHAR(50) DEFAULT 'v1.0',
    is_active BOOLEAN DEFAULT TRUE
);
```

#### 1.2 Update Certification Profile Storage
Keep existing database columns but clarify their purpose:

```sql
-- These remain as profile-specific prompts
ALTER TABLE certification_profiles
    ALTER COLUMN assessment_prompt SET DEFAULT NULL,
    ALTER COLUMN presentation_prompt SET DEFAULT NULL,
    ALTER COLUMN gap_analysis_prompt SET DEFAULT NULL;

-- Add comments to clarify purpose
COMMENT ON COLUMN certification_profiles.assessment_prompt IS 'Profile-specific prompt for assessment generation';
COMMENT ON COLUMN certification_profiles.presentation_prompt IS 'Profile-specific prompt for presentation generation';
COMMENT ON COLUMN certification_profiles.gap_analysis_prompt IS 'Profile-specific prompt for gap analysis';
```

### Phase 2: Backend API Changes 🔌

#### 2.1 New Knowledge Base Prompt Endpoints
Create dedicated endpoints for knowledge base prompt management:

```python
# src/service/api/v1/endpoints/knowledge_prompts.py

@router.get("/knowledge-prompts/{collection_name}")
async def get_knowledge_base_prompts(collection_name: str):
    """Get knowledge base-level prompts for a collection."""
    pass

@router.put("/knowledge-prompts/{collection_name}")
async def update_knowledge_base_prompts(collection_name: str, prompts: KnowledgeBasePrompts):
    """Update knowledge base-level prompts for a collection."""
    pass
```

#### 2.2 Update Certification Profile Endpoints
Modify existing endpoints to handle only profile-level prompts:

```python
# src/service/api/v1/endpoints/certifications.py

# Remove _chromadb_prompts from assessment_template
# Keep only database column prompts in responses:
response_data = {
    # ... other fields
    'assessment_prompt': profile.assessment_prompt,  # Profile-specific only
    'presentation_prompt': profile.presentation_prompt,  # Profile-specific only
    'gap_analysis_prompt': profile.gap_analysis_prompt,  # Profile-specific only
}
```

#### 2.3 Knowledge Base Service Updates
Update knowledge base operations to use collection-level prompts:

```python
# src/knowledge/base.py

class RAGKnowledgeBase:
    async def get_collection_prompts(self, collection_name: str) -> KnowledgeBasePrompts:
        """Get prompts for knowledge base operations."""
        pass

    async def ingest_with_prompts(self, documents: List, prompts: KnowledgeBasePrompts):
        """Use collection-specific prompts for ingestion."""
        pass
```

### Phase 3: Frontend Component Separation 🎨

#### 3.1 Split PromptEditor Components
Create separate components for different prompt types:

```typescript
// src/components/prompts/CertificationPromptEditor.tsx
interface CertificationPromptEditorProps {
  initialPrompts: {
    assessment_prompt?: string;
    presentation_prompt?: string;
    gap_analysis_prompt?: string;
  };
  onPromptsChange: (prompts) => void;
}

// src/components/prompts/KnowledgeBasePromptEditor.tsx
interface KnowledgeBasePromptEditorProps {
  collectionName: string;
  initialPrompts: {
    document_ingestion_prompt?: string;
    context_retrieval_prompt?: string;
    semantic_search_prompt?: string;
  };
  onPromptsChange: (prompts) => void;
}
```

#### 3.2 Update Form Integration
Modify forms to use appropriate prompt editors:

```typescript
// EnhancedCertificationProfileForm.tsx - Use CertificationPromptEditor
// KnowledgeBaseManagementForm.tsx - Use KnowledgeBasePromptEditor
```

### Phase 4: Data Migration 📦

#### 4.1 Migrate Existing Prompts
Create migration script to separate existing prompts:

```python
# migration_script.py

async def migrate_prompts():
    """Migrate existing prompts to new structure."""
    profiles = await get_all_profiles()

    for profile in profiles:
        # Extract knowledge base prompts from assessment_template
        if profile.assessment_template and '_chromadb_prompts' in profile.assessment_template:
            kb_prompts = profile.assessment_template['_chromadb_prompts']

            # Create knowledge base prompt record
            await create_knowledge_base_prompts(
                collection_name=profile.knowledge_base_path,
                prompts=extract_kb_prompts(kb_prompts)
            )

            # Keep only profile-specific prompts in database columns
            profile.assessment_prompt = profile.assessment_prompt or kb_prompts.get('assessment_prompt')
            profile.presentation_prompt = profile.presentation_prompt or kb_prompts.get('presentation_prompt')
            profile.gap_analysis_prompt = profile.gap_analysis_prompt or kb_prompts.get('gap_analysis_prompt')

            # Remove _chromadb_prompts from assessment_template
            if '_chromadb_prompts' in profile.assessment_template:
                del profile.assessment_template['_chromadb_prompts']

        await update_profile(profile)
```

### Phase 5: Default Prompt Management 🎯

#### 5.1 Separate Default Prompts
Update `src/service/default_prompts.py` to provide defaults for both contexts:

```python
def get_default_certification_prompts() -> Dict[str, str]:
    """Default prompts for certification profile operations."""
    return {
        'assessment_prompt': DEFAULT_ASSESSMENT_PROMPT,
        'presentation_prompt': DEFAULT_PRESENTATION_PROMPT,
        'gap_analysis_prompt': DEFAULT_GAP_ANALYSIS_PROMPT
    }

def get_default_knowledge_base_prompts() -> Dict[str, str]:
    """Default prompts for knowledge base operations."""
    return {
        'document_ingestion_prompt': DEFAULT_INGESTION_PROMPT,
        'context_retrieval_prompt': DEFAULT_RETRIEVAL_PROMPT,
        'semantic_search_prompt': DEFAULT_SEARCH_PROMPT
    }
```

#### 5.2 Auto-Population Logic
Implement smart defaults when creating new profiles:

```python
async def create_certification_profile(profile_data: CertificationProfileCreate):
    # Auto-populate with defaults if not provided
    if not profile_data.assessment_prompt:
        profile_data.assessment_prompt = get_default_certification_prompts()['assessment_prompt']

    # Create knowledge base prompts separately
    await ensure_knowledge_base_prompts_exist(
        collection_name=generate_collection_name(profile_data),
        defaults=get_default_knowledge_base_prompts()
    )
```

## Testing Strategy 🧪

### Unit Tests
- Test prompt separation in API responses
- Test knowledge base prompt CRUD operations
- Test certification prompt CRUD operations
- Test migration script functionality

### Integration Tests
- Test end-to-end prompt usage in assessment generation
- Test end-to-end prompt usage in knowledge base operations
- Test frontend form submission with separated prompts

### Manual Testing
- Create new certification profile → verify separate prompts
- Modify knowledge base prompts → verify no impact on profile prompts
- Modify profile prompts → verify no impact on knowledge base operations

## Implementation Timeline 📅

### Week 1: Database & Backend Foundation
- [ ] Create new `knowledge_base_prompts` table
- [ ] Implement knowledge base prompt endpoints
- [ ] Update certification profile endpoints to remove _chromadb_prompts

### Week 2: Knowledge Base Integration
- [ ] Update RAGKnowledgeBase to use collection prompts
- [ ] Update ingestion services to use collection prompts
- [ ] Test knowledge base operations with new prompt system

### Week 3: Frontend Components
- [ ] Create separate prompt editor components
- [ ] Update certification profile forms
- [ ] Create knowledge base prompt management UI

### Week 4: Migration & Testing
- [ ] Create and test migration script
- [ ] Run migration on development data
- [ ] Comprehensive testing of separated systems
- [ ] Documentation updates

## Success Criteria ✅

1. **Complete Separation**: Knowledge base and certification profile prompts are completely independent
2. **No Data Loss**: All existing prompts are preserved during migration
3. **Backward Compatibility**: Existing workflows continue to function
4. **Clear UX**: Users understand the difference between prompt types
5. **Improved Maintainability**: Changes to one prompt type don't affect the other

## Risk Mitigation 🛡️

### Data Loss Risk
- **Mitigation**: Comprehensive backup before migration + rollback plan
- **Testing**: Thorough validation of migration script on test data

### Breaking Changes Risk
- **Mitigation**: Feature flags for gradual rollout
- **Testing**: Parallel testing of old vs new systems

### User Confusion Risk
- **Mitigation**: Clear labeling and help text in UI
- **Documentation**: User guide explaining prompt types and their purposes

## Files to Modify 📁

### Backend
- `src/models/certification.py` - Add knowledge base prompt model
- `src/schemas/certification.py` - Remove _chromadb_prompts references
- `src/service/api/v1/endpoints/certifications.py` - Clean up prompt handling
- `src/service/api/v1/endpoints/knowledge_prompts.py` - New endpoint file
- `src/knowledge/base.py` - Update to use collection prompts
- `src/service/default_prompts.py` - Separate default prompts

### Frontend
- `presgen-ui/src/components/prompts/CertificationPromptEditor.tsx` - New component
- `presgen-ui/src/components/prompts/KnowledgeBasePromptEditor.tsx` - New component
- `presgen-ui/src/components/certification/EnhancedCertificationProfileForm.tsx` - Update
- `presgen-ui/src/app/api/presgen-assess/certifications/[id]/route.ts` - Update proxy

### Database
- Migration script for new table and data transfer
- Update existing table comments and constraints