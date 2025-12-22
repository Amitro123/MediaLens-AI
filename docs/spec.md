# Technical Specification: DevLens AI

## 1. System Goals

To build an automated full-stack pipeline that accepts video inputs and outputs high-quality technical documentation by leveraging LLM multimodal capabilities with:
- **Calendar Integration** for context-aware session management
- **Google Drive Import** for seamless video retrieval (public & authenticated)
- **Audio-First & Combined Multimodal Sampling** for cost and performance optimization
- **Visual Quality Control** for stable and clear documentation (filtering spinners/blurs)
- **Groq STT** for ultra-fast Whisper-based transcription with timestamps
- **Active Session Recovery** for persistent processing across browser refreshes
- **Click-to-Seek Navigation** for interactive video timestamp jumping from documentation images
- **Zombie Session Cleanup** for automatic expiration of stale processing tasks
- **Native Google Drive Integration** via `google-api-python-client`
- **Backend Integration Test Suite** for core flow verification

## 2. Architecture Overview

### Client-Server Architecture with Smart Sampling

```
┌─────────────────────────────────────────────────────────────┐
│                   Calendar Service (Backend)                │
│  - Mock events (Design Review, Bug Triage, etc.)            │
│  - Auto-create draft sessions                               │
│  - Mode suggestion based on keywords                        │
│  - **Clean Startup**: Deterministic mocks, no stuck states  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Frontend (React) - Dual Interface               │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │ Calendar Dashboard   │  │  Manual Upload       │        │
│  │ - Upcoming meetings  │  │  - Mode selector     │        │
│  │ - Session cards      │  │  - File dropzone     │        │
│  │ - Drag & drop upload │  │  - Progress tracking │        │
│  └──────────────────────┘  └──────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                Backend (FastAPI) - Smart Pipeline            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         1. Proxy Generation (FFmpeg)                 │  │
│  │  - Create 1 FPS low-res MP4 for analysis             │  │
│  │  - Extract WAV audio for speech context               │  │
│  └──────────────────────────────────────────────────────┘  │
│                              │
│  ┌──────────────────────────▼───────────────────────────┐  │
│  │    2. Multimodal Analysis (Gemini Flash)             │  │
│  │  - Fast analysis of 1 FPS Video + Audio Proxy        │  │
│  │  - **Visual QC**: Identify and skip loading spinners  │  │
│  │  - Select precise key timestamps for documentation   │  │
│  └──────────────────────────────────────────────────────┘  │
│                              │
│  ┌──────────────────────────▼───────────────────────────┐  │
│  │    3. High-Res Frame Extraction (OpenCV)             │  │
│  │  - Extract from **Original High-Qual Video**         │  │
│  │  - Only at AI-selected high-quality timestamps       │  │
│  └──────────────────────────────────────────────────────┘  │
│                              │
│  ┌──────────────────────────▼───────────────────────────┐  │
│  │  4. Documentation Generation (Gemini 1.5 Pro)        │  │
│  │  - Load context-aware prompt from YAML               │  │
│  │  - Inject meeting details and Visual QC rules        │  │
│  │  - Generate Markdown from pristine high-res frames   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  5. Chunk-based Processing (Optional)                │  │
│  │  - Split video into 30s segments                     │  │
│  │  - Process each segment independently                │  │
│  │  - Merge segment docs into final document            │  │
│  │  - Granular progress: "Segment 2/5"                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 2.1 Observability: Acontext Flight Recorder

The pipeline is instrumented with **Acontext** for full observability and debugging.

```
┌─────────────────────────────────────────────────────────────┐
│                    Acontext Integration                     │
│                                                             │
│  @trace_pipeline decorator → AcontextClient → Acontext API  │
│                                                             │
│  Traced Functions:                                          │
│  • extract_audio() - FFmpeg audio extraction                │
│  • analyze_audio_relevance() - Gemini Flash analysis        │
│  • extract_frames() - OpenCV frame extraction               │
│  • generate_documentation() - Gemini Pro generation         │
│                                                             │
│  Artifacts Stored:                                          │
│  • {task_id}_docs.md - Generated documentation              │
│  • {task_id}_code_N.{ext} - Extracted code blocks           │
└─────────────────────────────────────────────────────────────┘
```

**Key Files:**
- `backend/app/core/observability.py` - AcontextClient and @trace_pipeline decorator
- `docker-compose.yml` - Acontext + Redis infrastructure
- `backend/app/core/config.py` - Settings (ACONTEXT_URL, ACONTEXT_ENABLED)

## 2.2 SessionManager: Pipeline Orchestrator

The `SessionManager` is the **single authoritative source** for all session state, replacing fragmented state previously spread across `task_results`, `CalendarWatcher`, and `StorageService`.

```
┌─────────────────────────────────────────────────────────────┐
│                    SessionManager API                        │
│                                                             │
│  create_session(id, metadata)   → Creates draft session     │
│  start_processing(id)           → Initializes progress      │
│  update_progress(id, stage, %)  → Updates 0-100%            │
│  complete(id, path, doc)        → Finalizes with docs       │
│  fail(id, error)                → Marks failed              │
│  get_status(id)                 → Returns status dict       │
│  get_active_session()           → Finds active session      │
│                                                             │
│  Features:                                                  │
│  • Zombie cleanup (auto-expires stale sessions)             │
│  • Disk persistence via StorageService                      │
│  • In-memory cache for fast lookups                         │
└─────────────────────────────────────────────────────────────┘
```

**Key Files:**
- `backend/app/services/session_manager.py` - SessionManager class
- `backend/app/api/routes.py` - Delegates to SessionManager

## 2.3 DevLensAgent: Single Orchestrator

The `DevLensAgent` is the **main orchestrator** for video documentation generation, coordinating VideoProcessor, AIGenerator, and SessionManager.

```
┌─────────────────────────────────────────────────────────────┐
│                    DevLensAgent API                         │
│                                                             │
│  generate_documentation(                                    │
│      session_id,                                            │
│      video_path,                                            │
│      options: DevLensAgentOptions                           │
│  ) → DevLensResult                                          │
│                                                             │
│  Options:                                                   │
│  • mode - Prompt mode (bug_report, feature_spec, etc.)      │
│  • language - Output language                               │
│  • project_name - Project title                             │
│  • calendar_event_id - Context enrichment                   │
│  • use_segmented_pipeline - Enable chunk processing         │
└─────────────────────────────────────────────────────────────┘
```

**Key Files:**
- `backend/app/services/agent_orchestrator.py` - DevLensAgent class
- `backend/app/api/routes.py` - Uses agent for /upload endpoints

## 2.4 Fast STT Service: Local Audio Transcription

The `FastSttService` provides **~10x faster** audio transcription using local faster-whisper with automatic Gemini fallback.

```
┌─────────────────────────────────────────────────────────────┐
│                    FastSttService API                       │
│                                                             │
│  transcribe_video(audio_path) → SttResult                   │
│                                                             │
│  SttResult:                                                 │
│  • segments - [{"start", "end", "text"}]                    │
│  • processing_time_ms - Performance metric                  │
│  • model_used - "faster_whisper_small" or "gemini_fallback" │
│                                                             │
│  Config:                                                    │
│  • FAST_STT_ENABLED=True (default)                          │
│  • FAST_STT_MODEL="small" (tiny/base/small/medium)          │
└─────────────────────────────────────────────────────────────┘
```

**Key Files:**
- `backend/app/services/stt_fast_service.py` - FastSttService class
- `backend/app/services/ai_generator.py` - Uses STT for relevance analysis

## 3. API Endpoints (FastAPI)

### Calendar & Session Management

#### `GET /api/v1/sessions/drafts`
Get all draft sessions created from calendar events.

**Response:**
```json
[
  {
    "id": "evt_1",
    "title": "Design Review: User Profile",
    "time": "2025-12-16T10:00:00",
    "status": "scheduled",
    "context_keywords": ["profile", "settings", "ui"]
  },
  {
    "id": "evt_2",
    "title": "Bug Bash: Login Errors",
    "time": "2025-12-16T14:00:00",
    "status": "scheduled",
    "context_keywords": ["auth", "login", "500 error"]
  }
]
```

#### `POST /api/v1/sessions/{session_id}/prep`
Prepare a session for upload (prime context).

**Input:**
- `session_id`: Session UUID (path parameter)

**Process:**
1. Validate session exists
2. Update session status to "ready_for_upload"
3. (Future) Trigger pre-fetching of related documents (RAG)

**Response:**
```json
{
  "status": "ready_for_upload",
  "id": "session_id"
}
```

#### `POST /api/v1/upload/{session_id}`
Upload video to a specific draft session with auto-context injection.

**Input:**
- `session_id`: Session UUID (path parameter)
- `file`: Video file (multipart/form-data)
- `mode`: Optional mode override (uses suggested_mode if not provided)

**Process:**
1. Validate session exists and status is "ready_for_upload" (or "waiting_for_upload")
2. ...


#### `POST /api/v1/import/drive`
Import video from Google Drive (Native).

**Input:**
- `file_uri`: drive://file-id
- `file_name`: Name of file
- `mode`: Processing mode

**Process:**
1. Connect to Drive MCP server
2. Download binary content to task directory
3. Trigger standard pipeline


#### `POST /api/v1/sessions/{session_id}/feedback`
Submit user feedback and ratings.

**Input:**
- `rating`: Integer (1-5)
- `comment`: Optional string
- `section_id`: Optional specific section

**Response:**
```json
{ "status": "success" }
```

#### `POST /api/v1/sessions/{session_id}/export`
Export documentation to external services.

**Input:**
- `target`: "jira" | "notion" | "clipboard"

**Response (Jira):**
```json
{
  "status": "success",
  "message": "Jira ticket created: BUG-ABC1",
  "ticket_id": "BUG-ABC1"
}
```

**Response (Notion):**
```json
{
  "status": "success",
  "message": "Notion page created: Session abc123",
  "page_url": "https://notion.so/Engineering-Docs/abc123"
}
```
```

#### `GET /api/v1/active-session`
Retrieve any currently active processing or uploading session for UI recovery.

**Process:**
1. Scans `CalendarWatcher` for sessions in `processing` or `downloading_from_drive`
2. Scans in-memory `task_results` for manual uploads in `processing`
3. Returns the latest active session with its status and mode metadata

**Response:**
```json
{
  "session_id": "session_123",
  "status": "processing",
  "title": "Design Review",
  "mode": "feature_spec"
}
```

#### `GET /api/v1/status/{task_id}`
Get real-time status and progress percentage.
- Supports both manual and calendar-backed sessions.
- Automatically maps internal status codes to numeric progress.
- **Zombie Cleanup**: Checks `last_updated`; if >10m stale, marks as failed.

#### `POST /api/v1/sessions/{session_id}/cancel`
Manually cancel a stuck or unwanted processing session.

#### `GET /api/v1/integrations/drive/files`
List available video files from Google Drive.


### Manual Upload (Legacy)
...

## 6. Frontend Architecture

### Unified Interface Design

**Meeting Selector (Top)**
- Fetches draft sessions from `/api/v1/sessions/drafts`
- visual states:
    - **Scheduled**: Grey border, "⚡ Prep Context" button
    - **Ready**: Green border/glow, "Ready for Upload" indicator
    - **Processing**: Pulse animation during prep
- Clicking "Prep Context" calls API to prime session
- Clicking "Ready" card focuses Upload Area

**Upload Area (Bottom)**
- Context-aware header ("Upload for: Design Review")
- Adapts to selected session (pre-fills project name, mode)
- Falls back to manual mode if no session selected

### Components

**Dashboard.jsx**
- Orchestrates MeetingSelector and UploadForm
- Manages `selectedSession` state
- Handles smooth scrolling to upload area
- **Developer Mode**: Toggle switch to enable advanced telemetry
- **Telemetry Card**: Displays real-time processing stats, costs, and RAG sources (visible in Dev Mode)

**MeetingSelector.jsx**
- Grid of meeting cards
- Handles "Prep" API calls
- Manages local status updates (optimistic UI)

**UploadForm.jsx**
- Accepts optional `session` prop
- Tabbed Interface: "Upload Video" and "Import from Drive"
- Dynamically selects API endpoint:
  - File: `/upload/{id}` or `/upload`
  - Drive: `/upload/drive`
- Pre-fills form fields based on session context
- **DocViewer**: Renders generated markdown with "Rate this Doc" feedback loop and Export dropdown
  - **Feedback UI**: Thumbs up/down with optional comment
  - **Export Options**: Copy to clipboard, Send to Notion, Create Jira ticket
  - **Click-to-Seek Video Player**: Collapsible video player with timestamp navigation
    - Images display timestamp badges (⏱️ MM:SS)
    - Click any image to seek to that moment in the source video
    - Auto-expands player on click and starts playback
- **ROI Badge**: Displays time saved per document (~30 mins)
- **Department Grouping**: Modes organized by department (R&D, HR, Finance) with color-coded badges

## 7. Performance Optimizations

### Audio-First Smart Sampling

**Traditional Approach:**
- Extract 1 frame every 5 seconds
- 10-minute video = 120 frames
- Cost: ~$0.50 per video
- Processing time: ~30 seconds

**Smart Sampling Approach:**
- Extract audio: ~2 seconds
- Analyze with Flash: ~5 seconds
- Identify 40% technical content
- Extract 48 frames (60% reduction)
- Cost: ~$0.11 per video (78% savings!)
- Processing time: ~20 seconds (33% faster)

### Cost Breakdown

| Step | Model | Cost per 10min video |
|------|-------|---------------------|
| Audio Analysis | Flash | $0.01 |
| Frame Upload (48 frames) | Pro | $0.05 |
| Documentation Generation | Pro | $0.05 |
| **Total** | | **$0.11** |

**vs Traditional:** $0.50 (78% savings)

## 8. Calendar Integration

### Mock Calendar Service (MVP)

```python
class CalendarWatcher:
    def check_upcoming_meetings(self, hours_ahead=24):
        """Returns mock events within time window"""
        
    def create_draft_session(self, event):
        """Creates session with pre-filled metadata"""
        
    def _suggest_mode(self, keywords):
        """Auto-suggests mode based on keywords"""
        # "bug", "issue" → bug_report
        # "feature", "design" → feature_kickoff
        # "API", "docs" → general_doc
```

### Future: Real Calendar Integration
- Google Calendar API
- Microsoft Outlook API
- Webhook-based sync
- OAuth authentication

## 9. Dependencies

### Backend (Updated)
```
fastapi==0.104.1
google-generativeai==0.3.1
google-api-python-client
google-auth-oauthlib
opencv-python==4.8.1.78
ffmpeg-python==0.2.0  # NEW: Audio extraction
pyyaml==6.0.1
pydantic==2.5.0
```

### System Requirements
- **FFmpeg** - Required for audio extraction
  - Windows: `choco install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Linux: `apt-get install ffmpeg`

## 10. Security Considerations

### API Key Management
- Store `GEMINI_API_KEY` in `.env`
- Never commit to version control
- Use environment variables in production

### File Upload Validation
- Validate file type (video formats only)
- Validate file size (max 500MB)
- Validate video duration (max 15 minutes)
- Sanitize file names
- Store in isolated upload directory

### Audio File Handling
- Temporary audio files cleaned up after processing
- Audio stored in same directory as video
- Automatic cleanup on session completion

## 11. Testing Strategy

### Audio-First Pipeline Testing
1. **Unit Tests:**
   - `test_extract_audio()` - Verify WAV output
   - `test_analyze_audio_relevance()` - Mock Flash response
   - `test_extract_frames_at_timestamps()` - Verify frame extraction

2. **Integration Tests:**
   - `tests/test_backend.py` - Verifies the full pipeline from upload to status to history using mocks for AI/Video layers.
   - `tests/test_active_session_recovery.py` - Verifies session persistence across system navigation.

3. **Performance Tests:**
   - Measure proxy generation vs full video analysis time.
   - Verify frame count reduction and cost savings on long recordings.

## 12. Deployment Strategy

### Production Considerations
- **FFmpeg** must be installed on server
- Gemini API rate limits (60 RPM for Flash, 10 RPM for Pro)
- Audio file storage and cleanup
- Session persistence (use database instead of in-memory)
- Calendar API authentication and token refresh

### Scaling
- Async processing with Celery for long videos
- Redis for session state management
- S3/Cloud Storage for video and audio files
- CDN for frontend static files
