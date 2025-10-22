# Prompt Override Implementation Plan

## 1. Backend Enhancements (PresGen Core/Data)

### 1.1 Centralise Default Prompt
```python
# src/agent/prompts.py
DEFAULT_REPORT_PROMPT = MULTI_SLIDE_SYSTEM_PROMPT

def get_default_report_prompt(max_sections: int = 10, max_script_chars: int = 700) -> str:
    return DEFAULT_REPORT_PROMPT.format(
        max_sections=max_sections,
        max_script_chars=max_script_chars,
    )
```

### 1.2 Accept Optional Overrides
```python
# src/mcp/tools/llm.py
def _call_gemini_once(p: SummarizeParams) -> Dict[str, Any]:
    system_prompt = p.custom_prompt or get_default_report_prompt(
        max_sections=p.max_sections,
        max_script_chars=p.max_script_chars,
    )
    ...

# src/mcp_lab/orchestrator.py
def orchestrate(..., llm_prompt: str | None = None):
    params = {
        "report_text": report_text,
        "max_sections": max_sections_hint,
        "max_bullets": 5,
        "max_script_chars": 700,
        "custom_prompt": llm_prompt,
    }
    s = _call_llm(params)
```

### 1.3 Extend Public APIs
```python
# src/service/http.py
class RenderRequest(BaseModel):
    report_text: str
    report_prompt: Optional[str] = None
    ...

@app.post("/render")
async def render(req: RenderRequest):
    res = orchestrate(
        req.report_text,
        slide_count=req.slides,
        llm_prompt=req.report_prompt,
        ...
    )

class DataAsk(BaseModel):
    ...
    report_prompt: Optional[str] = None

res = orchestrate_mixed(
    req.report_text,
    llm_prompt=req.report_prompt,
    ...
)
```

### 1.4 Expose Default Prompt Endpoint
```python
@app.get("/prompts/report")
async def get_report_prompt():
    return {
        "prompt": get_default_report_prompt(),
        "version": "2025.10",
    }
```

### 1.5 Cache Key Update
```python
llm_cache_key = (
    llm_key(report_text, 5, 700, llm_model)
    + f":msec={max_sections_hint}"
    + f":prompt={hashlib.sha256((llm_prompt or '').encode()).hexdigest()[:8]}"
)
```

## 2. Frontend Updates

### 2.1 Shared Hook
```tsx
// presgen-ui/src/hooks/useReportPrompt.ts
export function useReportPrompt() {
  const [prompt, setPrompt] = useState<string>('')
  useEffect(() => {
    fetch('/api/presgen/prompts/report')
      .then(res => res.json())
      .then(data => setPrompt(data.prompt ?? ''))
      .catch(() => setPrompt(''))
  }, [])
  return { prompt, setPrompt }
}
```

### 2.2 Core Form
```tsx
const { prompt, setPrompt } = useReportPrompt()
const [reportPrompt, setReportPrompt] = useState('')

useEffect(() => {
  setReportPrompt(prompt)
}, [prompt])

// JSX (below Upload Document)
<div className="space-y-2">
  <Label htmlFor="report_prompt">Report Prompt</Label>
  <Textarea
    id="report_prompt"
    value={reportPrompt}
    onChange={(e) => setReportPrompt(e.target.value)}
    placeholder="Edit the instructions sent to the LLM"
  />
</div>

// Submit payload
const requestData = {
  ...,
  report_prompt: reportPrompt.trim(),
}
```

### 2.3 Data Form
Replicate the same hook usage and field placement under the “Report File” control. Ensure `generateDataWithContext` payload includes `report_prompt`.

```tsx
const requestData = {
  ...,
  report_prompt: reportPrompt.trim(),
}
```

### 2.4 Proxy Route
```ts
// presgen-ui/src/app/api/presgen-data/generate-mvp/route.ts
const backendRequest = {
  ...,
  report_prompt: data.report_prompt?.trim() || undefined,
}
```

## 3. Testing & Validation
- **Unit**: request model validation (prompt optional), cache-key hash inclusion, default prompt helper.
- **Integration**: mock orchestrator ensuring custom prompt flows through; UI tests verifying textbox population/editing.
- **Manual**:
  1. Load forms → confirm default prompt appears.
  2. Modify prompt → generate slides → inspect logs showing custom prompt hash.
  3. Clear field + reload → default reappears.

## 4. Review Checklist
- Prompt helper is single source of truth; no lingering literals.
- API compatibility maintained for consumers without prompt field.
- Cache invalidation documented (release notes).
- UI accessibility (label, textarea resizing) verified.
