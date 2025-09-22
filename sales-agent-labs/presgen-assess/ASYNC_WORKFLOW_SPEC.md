# PresGen-Assess Async Workflow & UI Specification

## Overview
This document details the async workflow requirements, UI specifications for the 40-slide support, and backend validation updates needed for PresGen-Assess.

## Async Workflow Design

### Problem Statement
The assessment workflow has a natural break point where users complete the assessment form externally. The user may close the PresGen application and return later to continue the workflow with the completed assessment results.

### Solution Architecture

#### Workflow State Management
```python
# src/models/workflow.py
class WorkflowStatus(Enum):
    INITIATED = "initiated"
    ASSESSMENT_GENERATED = "assessment_generated"
    DEPLOYED_TO_GOOGLE = "deployed_to_google"
    AWAITING_COMPLETION = "awaiting_completion"  # Async break point
    SHEET_URL_PROVIDED = "sheet_url_provided"
    RESULTS_ANALYZED = "results_analyzed"
    TRAINING_PLAN_GENERATED = "training_plan_generated"
    PRESENTATIONS_GENERATED = "presentations_generated"
    AVATAR_VIDEOS_GENERATED = "avatar_videos_generated"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class WorkflowState:
    id: UUID
    user_id: str
    certification_profile_id: UUID
    current_status: WorkflowStatus

    # Google Workspace resources
    google_form_url: Optional[str] = None
    google_sheet_id: Optional[str] = None
    google_drive_folder_url: Optional[str] = None

    # Assessment data
    assessment_data: Optional[dict] = None
    sheet_url_input: Optional[str] = None  # User-provided sheet URL
    gap_analysis_results: Optional[dict] = None
    training_plan: Optional[dict] = None
    generated_content: Optional[dict] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    paused_at: Optional[datetime] = None
    resumed_at: Optional[datetime] = None
```

#### Async Resume Endpoint
```python
# src/service/http.py
@app.post("/assess/resume-workflow")
async def resume_workflow(request: WorkflowResumeRequest):
    """Resume workflow with completed assessment sheet URL"""

    workflow_state = await workflow_manager.get_workflow(request.workflow_id)

    if workflow_state.current_status != WorkflowStatus.AWAITING_COMPLETION:
        raise HTTPException(
            status_code=400,
            detail="Workflow not in awaiting completion state"
        )

    # Validate Google Sheets URL
    if not validate_google_sheets_url(request.sheet_url):
        raise HTTPException(
            status_code=400,
            detail="Invalid Google Sheets URL provided"
        )

    # Update workflow state
    workflow_state.sheet_url_input = request.sheet_url
    workflow_state.current_status = WorkflowStatus.SHEET_URL_PROVIDED
    workflow_state.resumed_at = datetime.now()

    # Continue workflow asynchronously
    background_tasks.add_task(
        orchestrator.continue_workflow,
        workflow_state
    )

    return {
        "workflow_id": workflow_state.id,
        "status": "resumed",
        "next_steps": "Processing assessment results and generating content"
    }

@dataclass
class WorkflowResumeRequest:
    workflow_id: UUID
    sheet_url: str
    user_id: str
```

## Backend Validation Updates (40-Slide Support)

### Assessment Models with Slide Validation
```python
# src/models/assessment.py
from pydantic import BaseModel, Field, validator

class PresentationRequest(BaseModel):
    """Request model for presentation generation with 40-slide support"""

    title: str = Field(..., min_length=1, max_length=200)
    course_outline: dict
    slide_count: int = Field(default=20, ge=1, le=40)  # 1-40 slide validation
    learning_objectives: List[str]
    difficulty_level: str = Field(..., regex="^(beginner|intermediate|advanced)$")
    rag_context_required: bool = Field(default=True)

    @validator('slide_count')
    def validate_slide_count(cls, v):
        if not 1 <= v <= 40:
            raise ValueError('Slide count must be between 1 and 40')
        return v

    @validator('course_outline')
    def validate_course_outline_for_slides(cls, v, values):
        slide_count = values.get('slide_count', 20)

        # Ensure enough content sections for requested slides
        if len(v.get('sections', [])) * 3 < slide_count:
            raise ValueError(
                f'Insufficient content sections for {slide_count} slides. '
                f'Need at least {slide_count // 3} content sections.'
            )
        return v

class CourseOutline(BaseModel):
    """Course outline model with slide count validation"""

    title: str
    sections: List[dict]
    estimated_slides: int = Field(ge=1, le=40)
    duration_minutes: int = Field(ge=10, le=180)  # 10 min - 3 hours
    rag_sources: List[str] = Field(default_factory=list)

    @validator('estimated_slides')
    def validate_estimated_slides(cls, v):
        if not 1 <= v <= 40:
            raise ValueError('Estimated slides must be between 1 and 40')
        return v
```

### PresGen Integration Service Updates
```python
# src/integration/presgen_core.py
class PresGenCoreService:
    """Updated PresGen Core integration with 40-slide support"""

    async def create_presentation(
        self,
        request: PresentationRequest,
        rag_context: RAGContext
    ) -> PresentationResult:
        """Create presentation with enhanced validation and RAG context"""

        # Validate slide count against PresGen Core capabilities
        if request.slide_count > 40:
            raise ValidationError("PresGen Core maximum slide count is 40")

        # Prepare RAG-enhanced payload
        payload = {
            'title': request.title,
            'content_outline': request.course_outline,
            'slide_count': request.slide_count,
            'max_slides': 40,  # Inform PresGen Core of limit
            'rag_sources': rag_context.sources,
            'source_citations': rag_context.citations,
            'learning_objectives': request.learning_objectives,
            'target_audience': 'certification_preparation',
            'difficulty_level': request.difficulty_level,
            'content_requirements': {
                'include_citations': True,
                'reference_sources': True,
                'educational_focus': True
            }
        }

        # Extended timeout for larger presentations
        timeout = min(600, request.slide_count * 15)  # 15 seconds per slide

        try:
            response = await self.client.post(
                f"{self.base_url}/presentations/educational",
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            return PresentationResult.from_response(response.json())

        except httpx.TimeoutException:
            raise PresentationGenerationError(
                f"Timeout generating {request.slide_count}-slide presentation"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 413:
                raise PresentationGenerationError(
                    "Presentation too large for PresGen Core processing"
                )
            raise
```

## Frontend UI Specifications

### Slide Count Selector Component
```jsx
// frontend/components/SlideSelector.jsx
import React, { useState } from 'react';
import { Slider, TextField, Typography, Box, Alert } from '@mui/material';

export const SlideSelector = ({
  value = 20,
  onChange,
  disabled = false,
  showEstimatedTime = true
}) => {
  const [inputValue, setInputValue] = useState(value);
  const [error, setError] = useState('');

  const handleSliderChange = (event, newValue) => {
    setInputValue(newValue);
    setError('');
    onChange(newValue);
  };

  const handleInputChange = (event) => {
    const newValue = parseInt(event.target.value, 10);
    setInputValue(newValue);

    if (isNaN(newValue) || newValue < 1 || newValue > 40) {
      setError('Slide count must be between 1 and 40');
    } else {
      setError('');
      onChange(newValue);
    }
  };

  const estimatedMinutes = Math.ceil(inputValue * 2.5); // ~2.5 min per slide

  return (
    <Box sx={{ width: '100%', maxWidth: 400, margin: '20px 0' }}>
      <Typography gutterBottom>
        Number of Slides: {inputValue}
      </Typography>

      <Slider
        value={inputValue}
        onChange={handleSliderChange}
        min={1}
        max={40}
        step={1}
        marks={[
          { value: 1, label: '1' },
          { value: 10, label: '10' },
          { value: 20, label: '20' },
          { value: 30, label: '30' },
          { value: 40, label: '40' }
        ]}
        disabled={disabled}
        sx={{
          '& .MuiSlider-mark': {
            backgroundColor: '#bfbfbf',
            height: 8,
            width: 1,
          },
          '& .MuiSlider-markLabel': {
            fontSize: '0.75rem',
          }
        }}
      />

      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mt: 2 }}>
        <TextField
          label="Slides"
          type="number"
          value={inputValue}
          onChange={handleInputChange}
          inputProps={{ min: 1, max: 40 }}
          size="small"
          disabled={disabled}
          error={!!error}
          helperText={error}
          sx={{ width: 100 }}
        />

        {showEstimatedTime && (
          <Typography variant="body2" color="text.secondary">
            Est. {estimatedMinutes} min presentation
          </Typography>
        )}
      </Box>

      {inputValue > 30 && (
        <Alert severity="info" sx={{ mt: 2 }}>
          Large presentations (30+ slides) may take longer to generate and load.
        </Alert>
      )}
    </Box>
  );
};
```

### Workflow Resume Component
```jsx
// frontend/components/WorkflowResume.jsx
import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Link
} from '@mui/material';
import { validateGoogleSheetsUrl } from '../utils/validation';

export const WorkflowResume = ({ onResume }) => {
  const [sheetUrl, setSheetUrl] = useState('');
  const [workflowId, setWorkflowId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!workflowId.trim()) {
      setError('Workflow ID is required');
      return;
    }

    if (!validateGoogleSheetsUrl(sheetUrl)) {
      setError('Please provide a valid Google Sheets URL');
      return;
    }

    setLoading(true);

    try {
      await onResume({
        workflow_id: workflowId,
        sheet_url: sheetUrl
      });
    } catch (err) {
      setError(err.message || 'Failed to resume workflow');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{
        maxWidth: 600,
        margin: '40px auto',
        padding: 3,
        border: '1px solid #e0e0e0',
        borderRadius: 2
      }}
    >
      <Typography variant="h5" gutterBottom>
        Resume Assessment Workflow
      </Typography>

      <Typography variant="body2" color="text.secondary" paragraph>
        If you previously started an assessment and received Google Form/Sheet links,
        you can resume the workflow here by providing the completed assessment sheet URL.
      </Typography>

      <TextField
        label="Workflow ID"
        value={workflowId}
        onChange={(e) => setWorkflowId(e.target.value)}
        fullWidth
        margin="normal"
        required
        disabled={loading}
        helperText="Check your email or previous session for the workflow ID"
      />

      <TextField
        label="Completed Assessment Google Sheet URL"
        value={sheetUrl}
        onChange={(e) => setSheetUrl(e.target.value)}
        fullWidth
        margin="normal"
        required
        disabled={loading}
        placeholder="https://docs.google.com/spreadsheets/d/..."
        helperText="Copy the URL from your completed assessment Google Sheet"
      />

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ mt: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
        <Button
          type="submit"
          variant="contained"
          disabled={loading || !sheetUrl.trim() || !workflowId.trim()}
          startIcon={loading && <CircularProgress size={20} />}
        >
          {loading ? 'Resuming...' : 'Resume Workflow'}
        </Button>

        <Link
          href="#new-assessment"
          variant="body2"
          sx={{ textDecoration: 'none' }}
        >
          Start New Assessment Instead
        </Link>
      </Box>
    </Box>
  );
};
```

### Validation Utilities
```javascript
// frontend/utils/validation.js

export const validateGoogleSheetsUrl = (url) => {
  const pattern = /^https:\/\/docs\.google\.com\/spreadsheets\/d\/[a-zA-Z0-9-_]+/;
  return pattern.test(url);
};

export const validateSlideCount = (count) => {
  const num = parseInt(count, 10);
  return !isNaN(num) && num >= 1 && num <= 40;
};

export const estimatePresentationTime = (slideCount) => {
  // Estimate 2.5 minutes per slide average
  return Math.ceil(slideCount * 2.5);
};

export const getSlideCountRecommendation = (courseComplexity, topicCount) => {
  const baseSlides = Math.min(topicCount * 2, 20);

  switch (courseComplexity) {
    case 'beginner':
      return Math.min(baseSlides + 5, 25);
    case 'intermediate':
      return Math.min(baseSlides + 10, 35);
    case 'advanced':
      return Math.min(baseSlides + 15, 40);
    default:
      return 20;
  }
};
```

## Database Schema Updates

### Workflow State Table Updates
```sql
-- Add async workflow support columns
ALTER TABLE workflow_executions ADD COLUMN IF NOT EXISTS paused_at TIMESTAMP;
ALTER TABLE workflow_executions ADD COLUMN IF NOT EXISTS resumed_at TIMESTAMP;
ALTER TABLE workflow_executions ADD COLUMN IF NOT EXISTS sheet_url_input TEXT;
ALTER TABLE workflow_executions ADD COLUMN IF NOT EXISTS resume_token UUID DEFAULT gen_random_uuid();

-- Add slide count tracking
ALTER TABLE workflow_executions ADD COLUMN IF NOT EXISTS requested_slide_count INTEGER DEFAULT 20;
ALTER TABLE workflow_executions ADD COLUMN IF NOT EXISTS generated_slide_count INTEGER;

-- Create index for resume operations
CREATE INDEX IF NOT EXISTS idx_workflow_resume_token ON workflow_executions(resume_token);
CREATE INDEX IF NOT EXISTS idx_workflow_status_paused ON workflow_executions(execution_status, paused_at);
```

### Presentation Generation Tracking
```sql
-- Track presentation generation with slide counts
CREATE TABLE IF NOT EXISTS presentation_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_execution_id UUID REFERENCES workflow_executions(id),
    course_title VARCHAR(255) NOT NULL,
    requested_slides INTEGER NOT NULL CHECK (requested_slides >= 1 AND requested_slides <= 40),
    generated_slides INTEGER,
    generation_duration_seconds INTEGER,
    presgen_core_url TEXT,
    avatar_video_url TEXT,
    rag_sources_used TEXT[],
    generation_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_presentation_workflow ON presentation_generations(workflow_execution_id);
CREATE INDEX idx_presentation_slides ON presentation_generations(requested_slides);
```

## Configuration Updates

### Environment Variables
```bash
# Updated .env with async and slide support
ASYNC_WORKFLOW_ENABLED=true
MAX_SLIDES_SUPPORTED=40
WORKFLOW_RESUME_TOKEN_TTL_HOURS=72
PRESGEN_CORE_SLIDE_LIMIT=40
PRESENTATION_GENERATION_TIMEOUT_SECONDS=600
AVATAR_GENERATION_TIMEOUT_SECONDS=900
```

### Validation Configuration
```yaml
# config/validation.yaml
presentation:
  slide_count:
    min: 1
    max: 40
    default: 20
    recommendations:
      beginner: 15
      intermediate: 25
      advanced: 35

  timeouts:
    generation_per_slide_seconds: 15
    max_generation_seconds: 600
    avatar_per_slide_seconds: 22
    max_avatar_seconds: 900

workflow:
  async:
    enabled: true
    resume_token_ttl_hours: 72
    max_pause_duration_hours: 168  # 1 week

  validation:
    google_sheets_url_pattern: "^https://docs\\.google\\.com/spreadsheets/d/[a-zA-Z0-9-_]+"
    required_fields: ["workflow_id", "sheet_url"]
```

This specification provides the complete technical foundation for implementing async workflow support, 40-slide presentation capability, and enhanced UI components for PresGen-Assess.