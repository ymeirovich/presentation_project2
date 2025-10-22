# PresGen-Training + PresGen-Video Integration Plan

## Integration Architecture: Sequential Pipeline (Option A)

### **Flow Design:**
```
Text Script Input → PresGen-Training (1.4s) → PresGen-Video (Modified) → Final Presentation
```

### **Implementation Steps:**

#### **Step 1: Create Unified Orchestrator** 
- New file: `src/mcp/tools/unified_orchestrator.py`
- Combines PresGen-Training and PresGen-Video pipelines
- Handles text input → avatar video → enhanced presentation

#### **Step 2: Modify PresGen-Video Entry Point**
- Update `src/mcp/tools/video_orchestrator.py` to accept avatar videos
- Skip Phase 1 (audio/video extraction) when input is avatar video
- Start directly at Phase 2 (content analysis) with provided script text

#### **Step 3: Create Integration Interface**
- New endpoint: `/presentation/generate` (combines both pipelines)
- Input: `{"script": "text", "options": {...}}`
- Output: Professional presentation video

#### **Step 4: Update File Flow**
```
Input: text script
  ↓ 
PresGen-Training: script → avatar_video.mp4 + audio.wav
  ↓
PresGen-Video (Modified): 
  - Skip Phase 1 (use provided audio/video)  
  - Phase 2: Content analysis using original script text
  - Phase 3: Composition with bullet overlays
  ↓
Output: professional_presentation.mp4
```

### **Performance Target:**
- **PresGen-Training**: 1.4s (TTS + Avatar)
- **PresGen-Video Modified**: ~15s (Phase 2: 3s + Phase 3: 12s)
- **Total Pipeline**: ~16.4s (28% faster than current video-only pipeline)

### **API Design:**

```python
# Unified endpoint
POST /presentation/generate
{
  "script": "Hello, this is my presentation about...",
  "options": {
    "avatar_quality": "standard",  # fast|standard|high
    "bullet_style": "professional", 
    "output_format": "mp4"
  }
}

# Response
{
  "success": true,
  "output_path": "/tmp/jobs/{job_id}/final_presentation.mp4",
  "processing_time": 16.4,
  "phases": {
    "avatar_generation": 1.4,
    "content_analysis": 3.0, 
    "video_composition": 12.0
  }
}
```

### **File Structure:**
```
/tmp/jobs/{job_id}/
├── input/
│   └── script.txt                 # Original text input
├── avatar/
│   ├── audio.wav                  # Generated TTS
│   ├── avatar.png                 # Generated face image  
│   └── avatar_video.mp4           # PresGen-Training output
├── analysis/
│   └── slides.json                # Phase 2 content analysis
└── output/
    └── final_presentation.mp4      # Final result
```