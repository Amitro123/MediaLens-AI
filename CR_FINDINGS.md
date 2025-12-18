# Code Review Findings: DevLens AI

## 1. Architecture & Specification Compliance

### 1.1. Groq Integration Missing
**Severity:** High
**Description:** The `README.md` and `docs/spec.md` explicitly state that "Groq Whisper STT" is used for audio transcription ("Step 2: Transcribe with Groq"). However, the implementation in `backend/app/services/ai_generator.py` shows that the `GroqTranscriber` class is unused. Instead, the system uses `Gemini Flash` for audio analysis via `_transcribe_audio_fast`.
**Impact:** The system does not utilize the advertised "Ultra-fast Whisper-based transcription". This is a misleading architectural claim.
**Recommendation:** Integrate `GroqTranscriber` into the pipeline as specified, or update the documentation to reflect the actual use of Gemini Flash.

### 1.2. Branding Inconsistency
**Severity:** Low
**Description:** The project is named "DevLens AI" in `README.md`, but the backend code (e.g., `backend/app/main.py`) refers to it as "DocuFlow AI".
**Impact:** Confusion regarding the product name.
**Recommendation:** Unify branding across codebase and documentation.

## 2. Performance & Scalability

### 2.1. Blocking Operations in Async Routes
**Severity:** Critical
**Description:** The FastAPI application defines routes as `async def` (e.g., `upload_to_session`), but calls synchronous, blocking functions directly within them:
- `extract_frames` (OpenCV operations)
- `extract_audio` (FFmpeg subprocess)
**Impact:** These heavy CPU/IO bound operations will block the main event loop, making the server unresponsive to other requests during processing.
**Recommendation:** Offload these tasks to a thread pool using `fastapi.concurrency.run_in_threadpool` or `loop.run_in_executor`, or implement a proper background task queue (Celery) as mentioned in the roadmap.

### 2.2. In-Memory Persistence
**Severity:** Medium (Acceptable for MVP)
**Description:** Sessions, feedback, and task results are stored in global in-memory dictionaries (`draft_sessions`, `task_results`).
**Impact:** All data is lost upon server restart. Not suitable for production.
**Recommendation:** Implement a persistent database (PostgreSQL/SQLite) or Redis for session state.

## 3. Code Quality & Maintainability

### 3.1. Code Duplication in Upload Logic
**Severity:** Medium
**Description:** `upload_to_session` and `upload_from_drive` in `backend/app/api/routes.py` contain nearly identical pipelines for video processing (load prompt, validate duration, audio extraction, frame extraction, AI generation).
**Impact:** Violates DRY (Don't Repeat Yourself) principle, making maintenance difficult and bug-prone.
**Recommendation:** Refactor the processing pipeline into a shared service method (e.g., `process_video_session`) that handles the core logic regardless of the input source.

### 3.2. Unsafe String Interpolation
**Severity:** High
**Description:** `PromptLoader._interpolate_context` uses `str.format(**context)` to inject meeting details into prompts.
**Impact:**
1. **Crash Risk:** If the prompt (which is YAML/Text) contains `{}` braces for other purposes (e.g., JSON examples, code blocks), `format()` will raise a `KeyError` or `ValueError`.
2. **Security:** Potential for string formatting attacks if context values are not sanitized.
**Recommendation:** Use `string.Template` (safe substitution) or escape braces in prompts.

### 3.3. Unused Dependencies
**Severity:** Low
**Description:** `requirements.txt` lists `moviepy`, but the code uses `subprocess` to call `ffmpeg` directly.
**Recommendation:** Remove unused dependencies to reduce image size and complexity.

## 4. Frontend Observations

### 4.1. Fake Progress Bar
**Severity:** Low (UX)
**Description:** The frontend `UploadForm.jsx` uses `setInterval` to simulate progress up to 90%, having no real connection to the backend processing status.
**Impact:** Misleading user experience. Users might think the process is hanging at 90%.
**Recommendation:** Implement a polling mechanism (e.g., `/status/{task_id}`) to reflect actual progress, or use WebSockets.

### 4.2. Hardcoded Telemetry
**Severity:** Low
**Description:** `DocViewer.jsx` displays hardcoded mock telemetry data (`cost: "$0.004"`, etc.).
**Impact:** Misleading info presented as real data.
**Recommendation:** Connect telemetry to the backend response or clearly label it as "Mock Data".

### 4.3. Fragile State Management
**Severity:** Low
**Description:** In `UploadForm.jsx`, the logic for handling Drive uploads relies on checking `if (typeof file === 'string')`. This dual-purpose use of the `file` state variable is fragile.
**Recommendation:** Use separate state variables for `file` and `driveUrl`, or a discriminated union type structure.

---

## Resolution Status (2025-12-18)

| Issue | Status | Notes |
|-------|--------|-------|
| 1.1 Groq Integration | ✅ Resolved | Documentation updated to reflect actual Gemini Flash usage |
| 1.2 Branding | ✅ Resolved | Changed "DocuFlow AI" → "DevLens AI" in `main.py`, `prompt_loader.py`, `conftest.py` |
| 2.1 Blocking Operations | ✅ Resolved | Added `run_in_threadpool` wrappers in `routes.py` |
| 2.2 In-Memory Persistence | ✅ Documented | Added TODO comment (acceptable for MVP) |
| 3.1 Code Duplication | ✅ Resolved | Refactored into shared `video_pipeline.py` with `process_video_pipeline()` |
| 3.2 Unsafe String Interpolation | ✅ Resolved | Replaced with `string.Template.safe_substitute()` |
| 3.3 Unused Dependencies | ✅ Resolved | Removed `moviepy` from `requirements.txt` |
| 4.1 Fake Progress Bar | ✅ Documented | Acceptable for MVP - noted in codebase |
| 4.2 Hardcoded Telemetry | ✅ Resolved | Added "(Mock Data)" label in `DocViewer.jsx` |
| 4.3 Fragile State Management | ✅ Resolved | Refactored to use `videoFile`, `driveUrl`, `uploadMode` state |

