# 🛣️ DevLens AI Roadmap

This document outlines the planned features and development priorities for DevLens AI.

---

## ✅ Q4 2025: MVP Stabilization, Persistence & UX

The primary goal for this quarter is to solidify the MVP, ensure it's stable end-to-end, and provide a seamless user experience with memory persistence.

- [x] **MVP: Synchronous video processing**
- [x] **Dynamic prompt registry system**
- [x] **React frontend with mode selection (Dark Mode)**
- [x] **Calendar integration with draft sessions (mock events)**
- [x] **Audio-first smart sampling with Gemini Flash (legacy path)**
- [x] **Google Drive Integration (Import via URL / Native client)**
- [x] **Manual End-to-End Testing & Bug Fixes**
  - [x] Verify the entire flow: Video Upload → Doc Generation → History
  - [x] Fix Markdown rendering (images & tables)
  - [x] Resolve "White Screen" screenshots issue (Prompt Engineering)
- [x] **Video Processing Optimization**
  - [x] Implement 1-FPS downsampling for faster AI analysis
- [x] **Acontext Lite (History & Persistence)**
  - [x] Local storage based session history
  - [x] "History" tab in Frontend
  - [x] Active Session Recovery (Page refresh protection)
  - [x] Session JSON export (`session-{id}.json`) for debugging & integrations
  - [x] Dev Mode panel (raw JSON + pipeline metrics, dev-only)
- [x] **Interactive Click-to-Seek**
  - [x] Frontend video player integration
  - [x] Timestamp extraction and clickable key frames (12 moments)
- [x] **Fast STT Service**
  - [x] Local faster-whisper transcription (CPU, small model)
  - [x] Integrated into session pipeline (segments + transcript-like timeline)
  - [x] Automatic Gemini fallback when model unavailable
- [ ] **MCP Server Integration (Agent Connectivity) – optional / stretch**
  - [ ] Implement `fastapi-mcp` to expose memory endpoints
  - [ ] (Future) Connect Google Drive via external MCP server once stable

---

## 🚀 Q1 2026: "Smart Context" & Enhanced Distribution

Focus on making the agent smarter, securely shareable, and integrated with external tools.

- [ ] **Deep Link Sharing (Google Drive / DevLens)**
  - [ ] Generate links in Markdown that jump to specific timestamps in the DevLens player or Google Drive
  - [ ] Use existing session JSON (key_frames, segments) as the contract for link generation
- [ ] **Enterprise Grade Security**
  - [ ] Implement Basic Auth / Single Sign-On (SSO)
  - [ ] Secure sensitive folders (`uploads`, `data`) via .gitignore and access controls
- [ ] **Advanced OCR for Code Extraction**
  - [ ] Integrate PaddleOCR or similar OCR library for code/UI text in frames
- [ ] **Speaker Diarization**
  - [ ] Integrate `pyannote.audio` (or similar) to identify different speakers
- [ ] **Real Calendar API Integration**
  - [ ] Move from mock data to real Google Calendar / Outlook integration
- [ ] **Real Export API Integration**
  - [ ] Implement real Notion & Jira API calls using the generated docs + session JSON

---

## 🧠 Q2 2026: "Organizational Brain" & Production Readiness

Transition from a smart tool to a self-improving "organizational brain" ready for enterprise use.

- [ ] **Advanced RAG on Organizational Docs**
  - [ ] Implement entity linking (components, services, projects)
  - [ ] Use session JSON + docs as “experience corpus” for RAG
- [ ] **Self-Improving Memory Loop**
  - [ ] Use Acontext's "Experience Agent" (or similar loop) to learn from past sessions and refine prompts
- [ ] **Privacy-First Local Mode**
  - [ ] Support for local models via Ollama / on-prem LLMs
- [ ] **Full Async Processing**
  - [ ] Migrate to robust Celery + Redis (or similar) background worker queue
  - [ ] Keep HTTP/API contract identical to current synchronous flow

---

## 🌐 Future Vision: Multi-Language & Beyond

- [ ] **Multi-language Support (Hebrew/English)**
- [ ] **Alternative AI Writer Engines (Claude 3.5 Sonnet, etc.)**
- [ ] **Expanded Integrations**
  - [ ] Slack (push summaries + links)
  - [ ] Confluence / GitHub Wikis
  - [ ] Additional PM/issue trackers
