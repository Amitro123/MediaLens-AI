# 🛣️ DevLens AI Roadmap

This document outlines the planned features and development priorities for DevLens AI.

## ✅ Q4 2025: MVP Stabilization, Persistence & UX

The primary goal for this quarter is to solidify the MVP, ensure it's stable end-to-end, and provide a seamless user experience with memory persistence.

- [x] **MVP: Synchronous video processing**
- [x] **Dynamic prompt registry system**
- [x] **React frontend with mode selection (Dark Mode)**
- [x] **Calendar integration with draft sessions**
- [x] **Audio-first smart sampling with Gemini Flash**
- [x] **Google Drive Integration (Import via URL)**
- [x] **Manual End-to-End Testing & Bug Fixes**
    - [x] Verify the entire flow: Video Upload → Markdown Generation
    - [x] Fix Markdown rendering (images & tables)
    - [x] Resolve "White Screen" screenshots issue (Prompt Engineering)
- [x] **Video Processing Optimization**
    - [x] Implement 1-FPS downsampling for faster AI analysis
- [x] **Acontext Lite (History & Persistence)**
    - [x] Local storage based session history
    - [x] "History" tab in Frontend
    - [x] Active Session Recovery (Page refresh protection)
- [x] **Interactive Click-to-Seek** ✅
    - [x] Frontend video player integration
    - [x] Timestamp extraction and clickable images
- [x] **Fast STT Service** ✅
    - [x] Local faster-whisper transcription (~10x faster)
    - [x] Automatic Gemini fallback when model unavailable
- [ ] **MCP Server Integration (Agent Connectivity)**
    - [ ] Implement `fastapi-mcp` to expose memory endpoints
    - [ ] Connect Google Drive via MCP Client (for automation)

## 🚀 Q1 2026: "Smart Context" & Enhanced Distribution

Focus on making the agent smarter, securely shareable, and integrated with external tools.

- [ ] **Deep Link Sharing (Google Drive)**
    - [ ] Generate standard links in Markdown that point to specific timestamps in Google Drive video player (for email distribution).
- [ ] **Enterprise Grade Security**
    - [ ] Implement Basic Auth / Single Sign-On (SSO)
    - [ ] Secure sensitive folders (`uploads`, `data`) via .gitignore and access controls
- [ ] **Advanced OCR for Code Extraction**
    - [ ] Integrate PaddleOCR or a similar dedicated OCR library
- [ ] **Speaker Diarization**
    - [ ] Integrate `pyannote.audio` to identify different speakers
- [ ] **Real Calendar API Integration**
    - [ ] Move from mock data to real Google Calendar / Outlook integration
- [ ] **Real Export API Integration**
    - [ ] Implement real Notion & Jira API calls

## 🧠 Q2 2026: "Organizational Brain" & Production Readiness

Transition from a smart tool to a self-improving "organizational brain" ready for enterprise use.

- [ ] **Advanced RAG on Organizational Docs**
    - [ ] Implement entity linking (components, services, projects)
- [ ] **Self-Improving Memory Loop**
    - [ ] Use Acontext's "Experience Agent" to learn from past sessions
- [ ] **Privacy-First Local Mode**
    - [ ] Support for local models via Ollama
- [ ] **Full Async Processing**
    - [ ] Migrate to robust Celery + Redis background worker queue

## 🌐 Future Vision: Multi-Language & Beyond

- [ ] **Multi-language Support (Hebrew/English)**
- [ ] **Alternative AI Writer Engines (Claude 3.5 Sonnet)**
- [ ] **Expanded Integrations (Slack, Confluence, etc.)**
