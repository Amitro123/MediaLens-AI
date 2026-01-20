# AMIT CODING PREFERENCES v1.0
Session: 2026-01-17 - MediaLens Adaptation
Learned:
✅ Approved: [Smart Extraction Logic] → Pattern: Always initialize optional accumulation lists (e.g., `timestamps = []`) before conditional blocks to ensure ensuring stability if the condition (e.g., `relevant_segments`) is false but the variable is used later.
✅ Approved: [AI Mode Config] → Pattern: Use centralized YAML prompt configurations (`PromptLoader`) to decouple prompt engineering from code logic, allowing rapid iteration on AI personas.
✅ Approved: [Axios File Uploads] → Pattern: When using `FormData` with a global Axios instance that defaults to `application/json`, explicitly set `Content-Type: undefined` for the upload request to allow the browser to set the boundary.
✅ Approved: [Explicit Startup Validation] → Pattern: Always validate critical external dependencies keys (like API keys) on startup and log clear, actionable errors if missing (to prevent confusion later).
✅ Approved: [Granular Progress for Async] → Pattern: For tasks > 10s, implement a feedback loop (callback or session update) to report incremental progress to prevent "UI frozen" perception.
✅ Approved: [Mock Heavy ML Libs] → Pattern: When testing services with heavy ML imports (Torch, Tensorflow, Whisper), mock them in `sys.modules` at the top of the test file to ensure sub-second execution and avoid environment dependency hell.
✅ Approved: [Subprocess Durations] → Pattern: For critical path media duration checks, prefer lightweight `subprocess` calls (e.g., `ffprobe`) over loading heavy libraries, but ensure the tool is available in the environment.
✅ Approved: [Cloud API Fallback] → Pattern: When integrating cloud APIs for performance (e.g. Groq STT), always implement a robust local fallback (e.g. Whisper CPU) to ensure offline capability and reliability if quota/network fails.
✅ Approved: [User Choice AI] → Pattern: For critical AI features with performance/accuracy trade-offs (e.g. STT), expose a transparent choice to the user (Fast vs Accurate) rather than hardcoding a single path.
✅ Approved: [Sync API Types] → Pattern: When modifying backend Pydantic models (e.g. `ResultResponse`), immediately update the corresponding Frontend TypeScript interfaces (`api.ts`) to maintain type safety and avoid `as any` casting.
✅ Approved: [Comprehensive Mocks] → Pattern: When adding new fields to a core data class (e.g. `VideoPipelineResult`), aggressively grep and update all test mocks that instantiate it to prevent unrelated unit test failures.
✅ Approved: [Async Test Mocking] → Pattern: When mocking async methods (e.g., `transcribe`), explicitly use `AsyncMock` instead of `MagicMock` to ensure the awaited call is handled correctly by the test runner.
✅ Approved: [Frontend Test Sanity] → Pattern: When setting up a new test harness (e.g., Vitest), always start with a trivial sanity check (e.g. `Simple.test.tsx`) to validate the environment configuration before debugging complex component tests.
