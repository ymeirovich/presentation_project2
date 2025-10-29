# Presgen Core & Data - Current Architecture Documentation

**Project**: Sales Agent Labs / Presgen MVP
**Status**: Production-Ready (Completed August 2025)
**Version**: 1.0
**Last Updated**: October 24, 2025

---

## Executive Summary

Presgen is a **fully operational AI-powered SaaS platform** that transforms unstructured text reports and spreadsheet data into polished Google Slides presentations through intelligent summarization, data visualization, and automated slide generation. The system is built on a **multi-agent MCP (Model Context Protocol) architecture** with FastAPI backend, Next.js frontend, and deep integration with Google Cloud AI services.

---

## System Architecture Overview

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INTERFACES                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │  Next.js Web UI  │  │  Slack Bot       │  │  Direct HTTP │ │
│  │  (localhost:3000)│  │  /presgen        │  │  API Calls   │ │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬───────┘ │
└───────────┼────────────────────┼────────────────────┼─────────┘
            │                    │                    │
            └────────────────────┼────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│              FASTAPI HTTP SERVICE (port 8080)                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Endpoints:                                              │  │
│  │  - POST /render (PresGen Core: text → slides)           │  │
│  │  - POST /data/upload (Excel/CSV ingestion)              │  │
│  │  - POST /data/ask (PresGen Data: data → slides)         │  │
│  │  - POST /slack/events (Slack integration)               │  │
│  │  - POST /training/* (PresGen-Training endpoints)        │  │
│  │  - POST /video/* (PresGen-Video endpoints)              │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│           MCP ORCHESTRATOR (JSON-RPC Architecture)              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  orchestrate() - PresGen Core workflow                   │  │
│  │  orchestrate_mixed() - PresGen Data workflow             │  │
│  │  - Request ID management (idempotency)                   │  │
│  │  - Tool invocation via RPC client                        │  │
│  │  - Error handling & retry logic                          │  │
│  │  - Cache management                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              MCP TOOLS (Subprocess Communication)               │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐ │
│  │  llm.summarize │  │ imagen.generate│  │  slides.create   │ │
│  │  (Gemini 2.0)  │  │ (Vertex Imagen)│  │ (Google Slides)  │ │
│  └────────┬───────┘  └────────┬───────┘  └────────┬─────────┘ │
│           │                   │                    │            │
│  ┌────────┴───────────────────┴────────────────────┴─────────┐ │
│  │              data.query (DuckDB + Pandas)                  │ │
│  │  - SQL query generation (pattern + LLM fallback)           │ │
│  │  - Chart generation (matplotlib)                           │ │
│  │  - Drive upload & slide embedding                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    GOOGLE CLOUD SERVICES                        │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Vertex AI    │  │ Google Slides│  │ Google Drive API   │   │
│  │ - Gemini 2.0 │  │ API          │  │ - Image hosting    │   │
│  │ - Imagen     │  │ - Deck create│  │ - File sharing     │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    LOCAL STORAGE (Development)                  │
│  out/data/        - Parquet files from uploaded datasets        │
│  out/images/      - Generated charts & AI images                │
│  out/state/       - Idempotency cache & metadata                │
│  src/logs/        - Timestamped application logs                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend Core
- **Python 3.13** - Primary runtime
- **FastAPI 0.116.1** - Async HTTP server with automatic OpenAPI docs
- **Pydantic 2.11.7** - Request/response validation and schema enforcement
- **Uvicorn 0.35.0** - ASGI web server

### AI & Machine Learning
- **Google Vertex AI (Gemini 2.0 Flash)** - Text summarization, content generation
- **Vertex AI Imagen (imagegeneration@006)** - AI image generation from prompts
- **google-generativeai 0.8.5** - Gemini SDK
- **google-cloud-aiplatform 1.108.0** - Vertex AI integration

### Data Processing
- **DuckDB 1.3.2** - In-process analytical SQL database
- **Pandas 2.3.2** - Data manipulation and analysis
- **PyArrow 21.0.0** - Parquet file format support
- **Matplotlib 3.10.5** - Chart generation for data visualizations

### Google Cloud Integration
- **google-api-python-client 2.178.0** - Google Slides/Drive APIs
- **google-auth 2.40.3** - OAuth 2.0 authentication
- **google-cloud-storage 2.19.0** - Cloud Storage integration (planned)

### Frontend (presgen-ui/)
- **Next.js 14.x** - React framework with App Router
- **TypeScript** - Type-safe frontend development
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Reusable React component library
- **Radix UI** - Headless UI primitives

### Infrastructure & DevOps
- **Docker** - Containerization (planned for production)
- **ngrok 1.5.1** - Local HTTPS tunneling for Slack integration
- **pytest 8.4.1** - Testing framework
- **Black 25.1.0** - Code formatting
- **Ruff 0.12.9** - Fast Python linter

---

## Core Components & Data Flow

### 1. PresGen Core (Text → Slides)

**Entry Point**: `POST /render`

**Workflow**:
1. **User Input**: Text report (direct input or file upload via web UI)
2. **HTTP Service** (`src/service/http.py`):
   - Receives request with `report_text`, `slides` (count), `title`, `use_cache`
   - Validates input, generates unique `request_id` for idempotency
3. **Orchestrator** (`src/mcp_lab/orchestrator.py:orchestrate()`):
   - Calls `llm.summarize` tool to generate slide content
   - Calls `imagen.generate` for each slide (best effort, continues on failure)
   - Calls `slides.create` to build Google Slides deck
4. **MCP Tools** (`src/mcp/tools/`):
   - **llm.py**: Invokes Gemini 2.0 Flash with `MULTI_SLIDE_SYSTEM_PROMPT`
   - **imagen.py**: Generates images via Vertex Imagen API
   - **slides.py**: Creates presentation using Google Slides API
5. **Output**: Returns Google Slides URL to user

**Key Files**:
- `src/service/http.py` - FastAPI endpoints
- `src/mcp_lab/orchestrator.py` - Workflow coordination
- `src/mcp/tools/llm.py` - Gemini integration
- `src/mcp/tools/imagen.py` - Image generation
- `src/mcp/tools/slides.py` - Slides creation
- `src/agent/prompts.py` - System prompts for LLM

### 2. PresGen Data (Spreadsheets → Slides)

**Entry Points**:
- `POST /data/upload` - Upload Excel/CSV file
- `POST /data/ask` - Generate slides from data questions

**Workflow**:
1. **Data Upload**:
   - User uploads `.xlsx` or `.csv` file via web UI
   - `src/data/ingest.py:ingest_file()` converts to Parquet format
   - Stored in `out/data/{dataset_name}.parquet`
   - Schema extracted and returned to user

2. **Data Query & Slide Generation**:
   - User submits questions (e.g., "Which company generated most revenue?")
   - HTTP service calls `orchestrate_mixed()` with narrative + data questions
   - **Data Tool** (`src/mcp/tools/data.py:data_query()`):
     - **Query Understanding**: Pattern matching for common question types
     - **SQL Generation**: Maps question → DuckDB SQL query (with LLM fallback)
     - **Query Execution**: Runs SQL against Parquet dataset
     - **Chart Creation**: Generates matplotlib chart based on question intent
     - **Chart Selection Logic**: Intent-aware visualization type selection
       - Frequency/Count → Grouped bar chart
       - Revenue/Ranking → Bar chart
       - Trends over time → Line chart
       - Correlation → Scatter plot
     - **Bullet Generation**: AI-powered explanatory bullet points for each chart
     - **Drive Upload**: Uploads chart image to Google Drive
     - **Slide Creation**: Embeds chart in slide with bullets and title

3. **Mixed Orchestration**:
   - `orchestrate_mixed()` handles both narrative slides (text-based) and data slides
   - Smart allocation: Reserves slides for data questions, fills remainder with narrative
   - Each data question gets its own slide with chart + analysis

4. **Output**: Google Slides deck with narrative + data visualization slides

**Key Files**:
- `src/data/ingest.py` - Excel/CSV → Parquet conversion
- `src/data/catalog.py` - Dataset resolution and metadata
- `src/mcp/tools/data.py` - SQL generation, chart creation, slide embedding
- `src/mcp_lab/orchestrator.py:orchestrate_mixed()` - Mixed workflow

### 3. Agent Layer (Direct API Access)

**Purpose**: Legacy/debugging path with reusable modules for direct Google API calls

**Components**:
- `src/agent/llm_gemini.py` - Direct Gemini API wrapper
- `src/agent/imagegen_vertex.py` - Direct Vertex Imagen calls
- `src/agent/slides_google.py` - Google Slides API integration
  - OAuth authentication
  - Drive upload for images
  - Multi-strategy speaker notes insertion
- `src/agent/prompts.py` - System prompts and JSON schemas

**Note**: Primary architecture uses MCP tools, but agent modules are still used by MCP tool implementations for actual API calls.

### 4. Common Utilities

**`src/common/`** - Shared infrastructure:
- `config.py` - YAML config loader with environment variable substitution
- `jsonlog.py` - Structured JSON logging with request tracing
- `cache.py` - File-based caching for idempotency
- `backoff.py` - Exponential backoff retry logic

---

## MCP (Model Context Protocol) Architecture

### What is MCP?

MCP is a **JSON-RPC-based protocol** for tool orchestration. Each "tool" is a discrete capability (LLM call, image generation, slide creation) exposed via JSON-RPC over stdin/stdout.

### Why MCP?

1. **Clean Separation**: Each tool is independently testable
2. **Subprocess Isolation**: Tools run in separate processes, preventing conflicts
3. **Distributed Execution**: Tools can be scaled independently (future)
4. **Standardized Interface**: JSON-RPC provides consistent request/response format

### MCP Implementation

**Server**: `src/mcp/server.py`
- Persistent subprocess (loop-based architecture)
- Handles multiple JSON-RPC requests sequentially
- Tools registered at startup
- Logging redirected to stderr (stdout reserved for JSON-RPC)

**Client**: `src/mcp_lab/rpc_client.py:MCPClient`
- Manages subprocess lifecycle
- Sends JSON-RPC requests via stdin
- Reads responses from stdout
- Handles timeouts and subprocess crashes with auto-restart

**Tool Registration**: `src/mcp/schemas.py`
- Each tool has schema definition (name, parameters, timeout)
- Example timeouts:
  - `llm.summarize`: 120s
  - `imagen.generate`: 60s
  - `slides.create`: 600s (long timeout for Drive uploads)
  - `data.query`: 300s (data processing + chart generation)

### Tool Communication Flow

```
Orchestrator
    ↓ (Python function call)
MCPClient.call_tool(name="llm.summarize", params={...})
    ↓ (JSON-RPC over stdin)
MCP Server Subprocess
    ↓ (Imports and executes)
src/mcp/tools/llm.py:llm_summarize(...)
    ↓ (Direct API call)
Google Vertex AI (Gemini 2.0)
    ↓ (Response)
JSON-RPC response over stdout
    ↓
MCPClient receives response
    ↓
Orchestrator continues with next step
```

---

## Data Pipeline Deep Dive

### Data Ingestion

**File**: `src/data/ingest.py`

**Process**:
1. Accepts `.xlsx` or `.csv` file via FastAPI `UploadFile`
2. Reads into Pandas DataFrame
3. Infers schema (column names, types, sample values)
4. Converts to Parquet format for efficient storage
5. Saves to `out/data/{dataset_name}.parquet`
6. Returns schema metadata to user

**Why Parquet?**
- Columnar format = fast queries
- Compression = smaller storage
- DuckDB native support = no external database needed

### Query Understanding & SQL Generation

**File**: `src/mcp/tools/data.py:data_query()`

**Two-Stage Approach**:

1. **Pattern Matching (Primary)**:
   - Regex patterns for common question types
   - Example patterns:
     - "Total X by Y" → `SELECT Y, SUM(X) FROM data GROUP BY Y`
     - "Which X most Y" → `SELECT X, SUM(Y) FROM data GROUP BY X ORDER BY SUM(Y) DESC LIMIT 10`
     - "Trend over time" → `SELECT date, AVG(value) FROM data GROUP BY date ORDER BY date`
   - Fast, predictable, no API costs

2. **LLM Fallback (Secondary)**:
   - If patterns don't match, invoke Gemini with schema + question
   - LLM generates SQL query
   - Validates query before execution
   - More flexible but slower + API cost

### Chart Generation

**Intent-Aware Chart Selection**:
- Frequency/Distribution questions → **Grouped bar chart**
- Ranking/Comparison questions → **Bar chart**
- Trend over time → **Line chart**
- Correlation/Relationship → **Scatter plot**

**Implementation**:
```python
# src/mcp/tools/data.py
if "frequency" in question or "count" in question:
    chart_type = "grouped_bar"
elif "revenue" in question or "most" in question:
    chart_type = "bar"
elif "trend" in question or "over time" in question:
    chart_type = "line"
elif "relationship" in question or "correlation" in question:
    chart_type = "scatter"
```

**Chart Rendering**:
- Uses matplotlib with professional styling
- Saved as PNG to `out/images/{request_id}_chart_{n}.png`
- Uploaded to Google Drive for embedding

### Context-Aware Bullet Generation

**For each chart**, the system generates 2-3 explanatory bullet points:

**Process**:
1. Extract key insights from query results (top values, trends, patterns)
2. Send context to Gemini with specialized prompt
3. LLM generates human-readable bullet summaries
4. Bullets embedded in slide alongside chart

**Example**:
- Question: "Which company generated most revenue?"
- Bullets:
  1. "Acme Corp leads with $2.5M in total revenue"
  2. "Top 3 companies account for 67% of all revenue"
  3. "Significant drop-off after top 5 performers"

---

## Frontend Architecture (presgen-ui/)

### Technology Choices

**Next.js 14 with App Router**:
- Server-side rendering for performance
- File-based routing
- API route handlers (not used, backend is separate FastAPI)

**Tailwind CSS + shadcn/ui**:
- Utility-first styling
- Consistent design system
- Reusable accessible components

### Key Components

**`src/app/page.tsx`** - Main application page:
- Tabbed interface: PresGen-Core | PresGen-Data | PresGen-Video
- Client-side routing
- Persistent banner with info modals

**`src/components/CoreForm.tsx`** - Text → Slides form:
- Report text input (textarea) or file upload
- Slide count slider (3-15)
- Presentation title input
- Options: Cache control, AI images toggle, speaker notes toggle

**`src/components/DataForm.tsx`** - Spreadsheet → Slides form:
- Excel/CSV file upload with drag-drop
- Schema preview after upload
- Multiple question input (textarea, one per line)
- RAG context: Report text or report file upload
- Slide count (3-20), chart style, template style
- Dynamic validation

**`src/components/FileDrop.tsx`** - Reusable file upload:
- Drag-and-drop support
- File type validation
- Progress indicators
- Error handling

**`src/components/ServerResponseCard.tsx`** - Result display:
- Shows generated presentation link as "Open Slides" button
- Error messages with retry guidance
- Toast notifications for success/failure

**`src/lib/api.ts`** - API client:
- Centralized HTTP client for backend communication
- `generatePresentation()` - Calls `/render` endpoint
- `uploadDataset()` - Calls `/data/upload` endpoint
- `generateDataPresentation()` - Calls `/data/ask` endpoint
- Error handling and response parsing

**`src/lib/schemas.ts`** - TypeScript types matching backend Pydantic models

### Integration Points

**Frontend ↔ Backend Communication**:
- Frontend runs on `localhost:3000` (dev) or `localhost:3003` (prod)
- Backend runs on `localhost:8080`
- Proxied through ngrok for Slack integration: `https://*.ngrok-free.app`
- CORS enabled for local development

**Environment Variables** (`.env.local`):
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
```

---

## Authentication & Security

### Google Cloud Authentication

**Service Account** (for Vertex AI):
- Used for Gemini LLM and Imagen API calls
- JSON key file stored locally (not committed to git)
- Loaded via `GOOGLE_APPLICATION_CREDENTIALS` env var
- Roles: `Vertex AI User`, `Storage Admin`

**OAuth 2.0** (for Google Slides/Drive):
- User consent flow for Slides/Drive API access
- `oauth_slides_client.json` - OAuth client credentials
- `token.json` - Cached access/refresh tokens
- Scopes:
  - `https://www.googleapis.com/auth/presentations`
  - `https://www.googleapis.com/auth/drive.file`

**File**: `src/agent/slides_google.py:authenticate()`

### Slack Integration

**Webhook Signature Verification**:
- HMAC-SHA256 signature validation
- `SLACK_SIGNING_SECRET` environment variable
- Can be bypassed locally with `DEBUG_BYPASS_SLACK_SIG=1`

**Bot Token**:
- `SLACK_BOT_TOKEN` for API calls
- Used to post ephemeral responses and updates

### Input Validation

**FastAPI Pydantic Models**:
- Request validation at HTTP layer
- Type checking for all parameters
- Example: `RenderRequest` model in `src/service/http.py`

**File Upload Security**:
- File type restrictions (`.xlsx`, `.csv`, `.txt` only)
- File size limits (50MB max)
- Content validation before processing

---

## Caching & Idempotency

### Why Idempotency?

**Problem**: Users often retry slow operations (slide generation takes 30-60s)
**Solution**: Same request ID → same output, no duplicate slides created

### Implementation

**Request ID Generation**:
```python
# src/service/http.py
request_id = f"req-{int(time.time())}-{uuid.uuid4().hex[:8]}"
```

**Cache Storage**:
- File-based cache in `out/state/`
- Each operation caches:
  - LLM summarization results
  - Generated image URLs
  - Final slide deck URL
- Cache key = `request_id + operation_type`

**Cache Bypass**:
- User can set `use_cache: false` to force fresh generation
- Useful for iterating on presentations
- Environment variable: `PRESGEN_USE_CACHE=false` (development mode)

**TTL (Time To Live)**:
- Default: 24 hours
- Configurable via `--cache-ttl-hours` CLI flag
- Old cache entries cleaned up manually or via scheduled job

---

## Error Handling & Retry Logic

### Retry Strategy

**Exponential Backoff** (`src/common/backoff.py`):
- Retries on transient failures (rate limits, timeouts)
- Max retries: 3
- Backoff: 2^attempt seconds (2s, 4s, 8s)
- Applies to:
  - Vertex AI API calls (LLM, Imagen)
  - Google Slides/Drive API calls
  - DuckDB query execution

### Graceful Degradation

**Image Generation Failures**:
- If Imagen fails (safety filters, quota), slide is created text-only
- User receives warning in logs but presentation still generated

**Data Query Failures**:
- If SQL generation fails, creates text-only slide with error message
- Other data questions continue processing
- Presentation still delivered with partial results

**Timeout Handling**:
- Each MCP tool has timeout limit
- If timeout exceeded, orchestrator logs error and continues
- Example: `slides.create` timeout reduced from 10min → 5min for faster feedback

### Error Logging

**Structured Logging** (`src/common/jsonlog.py`):
- All logs in JSON format with timestamps
- Request ID tracing across all operations
- Saved to `src/logs/presgen-{timestamp}.log`
- GCP Cloud Logging disabled to save costs (local-first)

**Log Levels**:
- `DEBUG`: GCP API calls, subprocess communication
- `INFO`: Request start/end, major operations
- `WARNING`: Recoverable errors (image gen failures)
- `ERROR`: Critical failures (slide creation timeout)

---

## Performance Characteristics

### Typical Latencies

**PresGen Core** (Text → Slides):
- 5 slides, no images: ~20-30 seconds
- 5 slides, with images: ~45-60 seconds
- Breakdown:
  - LLM summarization: 10-15s
  - Image generation (per slide): 5-8s
  - Slides creation: 10-15s (includes Drive uploads)

**PresGen Data** (Spreadsheets → Slides):
- 10 slides (3 narrative + 7 data): ~60-90 seconds
- Breakdown:
  - Data query + chart gen (per question): 5-10s
  - LLM summarization: 10-15s
  - Slides creation: 20-30s (larger deck)

### Bottlenecks

1. **Google Drive Upload**:
   - Largest bottleneck for image-heavy presentations
   - Each image upload: 2-5 seconds
   - Mitigation: Base64 inline for small images (<1.5KB), Drive for larger

2. **Slides API Rate Limits**:
   - 100 requests/100 seconds per user
   - Each slide insertion = 1 request
   - Large decks (15+ slides) may hit limits

3. **LLM Token Processing**:
   - Gemini 2.0 Flash is fast but large reports take longer
   - Mitigated by setting max_output_tokens=8192

### Optimization Strategies

**Implemented**:
- Parallel image generation (future: use asyncio)
- Base64 inline images for small files
- Reduced timeouts for faster failure feedback
- Local caching to avoid redundant API calls

**Planned**:
- Batch slide insertion (single API call for multiple slides)
- Cloud Storage instead of Drive for image hosting
- Async/await throughout backend for better concurrency

---

## Deployment Configuration

### Current Setup (Development)

**Backend**:
```bash
cd sales-agent-labs
uvicorn src.service.http:app --reload --port 8080
```

**Frontend**:
```bash
cd presgen-ui
npm install
npm run dev  # Runs on localhost:3000 or 3003
```

**Ngrok Tunnel** (for Slack):
```bash
ngrok http 8080
# Update Slack webhook URL with ngrok HTTPS URL
```

### Environment Variables

**Required** (`.env` file):
```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./presgen-service-account.json

# Slack (optional)
SLACK_SIGNING_SECRET=your-secret
SLACK_BOT_TOKEN=xoxb-your-token

# Development
DEBUG_BYPASS_SLACK_SIG=1          # Skip Slack signature verification
PRESGEN_USE_CACHE=true            # Enable caching
ENABLE_LOCAL_DEBUG_FILE=true      # Log to src/logs/
```

### Production Deployment (Planned)

**Target Platform**: Google Cloud Run

**Changes Required**:
1. **Dockerfile**: Containerize FastAPI app
2. **Cloud Storage**: Replace `out/` directory with GCS buckets
3. **Secrets Manager**: Migrate env vars to Google Secret Manager
4. **Load Balancing**: Use Cloud Run automatic scaling
5. **Monitoring**: Enable GCP Cloud Logging and Error Reporting
6. **Database**: Optional PostgreSQL for user accounts and presentation history

---

## Testing Strategy

### Unit Tests

**Location**: `tests/` directory

**Coverage**:
- `test_orchestrator_live.py` - End-to-end orchestration with real APIs
- `test_cache_unit.py` - Cache functionality
- Individual tool tests (mocked APIs)

**Run**:
```bash
RUN_SMOKE=1 python -m pytest tests/ -v
```

### Integration Tests

**Manual Testing via Web UI**:
- PresGen Core: Upload text report, verify slides generated
- PresGen Data: Upload CSV, ask questions, verify charts embedded
- Error scenarios: Invalid file types, malformed questions

**Slack Testing**:
```bash
curl -X POST http://localhost:8080/slack/events \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test"}'
```

### Live API Tests

**Prerequisites**: Valid Google Cloud credentials

**Example**:
```bash
python -m src.mcp_lab examples/report_demo.txt --slides 3 --no-cache
```

---

## Known Limitations & Future Improvements

### Current Limitations

1. **No User Authentication**:
   - Anonymous slide generation
   - No user accounts or presentation history
   - Plan: Add Firebase Auth or Google Sign-In

2. **Local Storage Only**:
   - All data stored in `out/` directory
   - Not suitable for production multi-user deployment
   - Plan: Migrate to Google Cloud Storage

3. **Single-Threaded Processing**:
   - One presentation at a time per instance
   - Plan: Add async/await and worker queues (Celery + Redis)

4. **Limited Chart Types**:
   - Only 4 chart types (bar, line, scatter, grouped bar)
   - Plan: Add pie charts, heatmaps, area charts

5. **No Real-Time Feedback**:
   - User waits 30-60s with no progress updates
   - Plan: WebSocket-based progress streaming

6. **Slack Limitations**:
   - 3-second response window (must use background processing)
   - No rich interactive components
   - Plan: Add Slack modals and block actions

### Future Enhancements

**Short Term** (Next 30 Days):
- Production deployment to Cloud Run
- User accounts and authentication
- Presentation history dashboard
- Better error messages in web UI

**Medium Term** (3-6 Months):
- PresGen-Video MVP (video → slides with timed overlays)
- Advanced chart customization (colors, labels, styles)
- Template library (corporate, creative, minimal)
- API keys for external developers

**Long Term** (12+ Months):
- Multi-modal AI agent (text + data + video + voice)
- Real-time collaboration (live editing, comments)
- Enterprise features (team workspaces, approval workflows)
- Industry-specific templates and data connectors

---

## Critical Files Reference

### Configuration
- `.env` - Environment variables (secrets)
- `config.yaml` - Application configuration
- `requirements.txt` - Python dependencies
- `presgen-ui/package.json` - Frontend dependencies

### Backend Entry Points
- `src/service/http.py` - FastAPI server
- `src/mcp/server.py` - MCP JSON-RPC server
- `src/mcp_lab/orchestrator.py` - Workflow orchestration

### Core Tools
- `src/mcp/tools/llm.py` - Gemini integration
- `src/mcp/tools/imagen.py` - Vertex Imagen
- `src/mcp/tools/slides.py` - Google Slides API
- `src/mcp/tools/data.py` - Data processing & charts

### Agent Modules (Used by MCP Tools)
- `src/agent/llm_gemini.py` - Gemini wrapper
- `src/agent/imagegen_vertex.py` - Imagen wrapper
- `src/agent/slides_google.py` - Slides/Drive APIs
- `src/agent/prompts.py` - System prompts

### Frontend
- `presgen-ui/src/app/page.tsx` - Main app page
- `presgen-ui/src/components/CoreForm.tsx` - PresGen Core UI
- `presgen-ui/src/components/DataForm.tsx` - PresGen Data UI
- `presgen-ui/src/lib/api.ts` - Backend API client

### Documentation
- `README.md` - Project overview and setup
- `CONTEXT.md` - Development context and history
- `CHANGELOG.md` - Version history
- `presgen-ui/FRONTEND_DOCUMENTATION.md` - Frontend reference

---

## Appendix: MVP Requirements Met

### ✅ All Core Features Operational

**PresGen Core**:
- ✅ Text report → structured slide content
- ✅ AI image generation for each slide
- ✅ Google Slides deck creation
- ✅ Speaker notes insertion (multi-strategy)
- ✅ Cache/idempotency management
- ✅ Error handling and graceful degradation

**PresGen Data**:
- ✅ Excel/CSV upload and Parquet conversion
- ✅ Schema extraction and preview
- ✅ Natural language → SQL query generation
- ✅ Intent-aware chart selection
- ✅ Context-aware bullet generation
- ✅ Chart embedding in slides
- ✅ Mixed narrative + data slide orchestration

**Web Interface**:
- ✅ Professional Next.js UI with light theme
- ✅ Tabbed navigation (Core, Data, Video)
- ✅ File upload with drag-and-drop
- ✅ Real-time validation and error messages
- ✅ Clickable slide links in results
- ✅ Responsive design for all screen sizes

**Integration & Reliability**:
- ✅ Slack bot integration (/presgen command)
- ✅ HTTP API with OpenAPI docs
- ✅ Structured JSON logging
- ✅ Cost-effective local logging (no GCP charges)
- ✅ Comprehensive error tracking

### 🎯 Example Questions All Working

1. ✅ "Transaction frequency by company and day" → Grouped bar chart
2. ✅ "Which company generated most revenue?" → Bar chart with ranking
3. ✅ "Daily sales trend over 6 weeks" → Line chart with trend analysis
4. ✅ "Relationship between quantity and price" → Scatter plot with correlation

---

**For Questions or Issues**:
- See `README.md` for setup instructions
- See `CONTEXT.md` for development history
- Check `src/logs/` for application logs
- Review `.env.template` for required environment variables

**Status**: This document reflects the production-ready state of Presgen Core & Data as of October 2025. The system is fully functional and ready for production deployment.
