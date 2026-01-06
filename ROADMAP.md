# 🛣️ DevLens AI Roadmap

This document outlines the planned features and development priorities for DevLens AI.

---

## ✅ Completed (Q4 2025 + New)

- [x] **MVP Core + Calendar + Drive + STT**
- [x] **Hebrish STT** (85%, ivrit-ai live!)
- [x] **Video Timeline + Click-to-Seek**
- [x] **FastSTT + Chunk Processing**
- [x] **Active Recovery + Tests**
- [x] **Multi-Department Personas**
- [x] **Demo.mp4 E2E** (85% accuracy)

### Q4 2025 Details
- [x] MVP: Synchronous video processing
- [x] Dynamic prompt registry system
- [x] React frontend with mode selection (Dark Mode)
- [x] Calendar integration with draft sessions (mock events)
- [x] Audio-first smart sampling with Gemini Flash
- [x] Google Drive Integration (Import via URL / Native client)
- [x] Video Processing Optimization (1-FPS downsampling)
- [x] Acontext Lite (History & Persistence)
- [x] Interactive Click-to-Seek (12 moments)
- [x] Fast STT Service (local faster-whisper, CPU)
- [x] Active Session Recovery
- [x] Dev Mode panel (raw JSON + pipeline metrics)

---

## 🔥 PRIORITY 1 (Q1 2026) – This Week

- [ ] **Kaggle Fine-tune Hebrish** (95% accuracy target)
- [ ] **Post-Process LLM** (אבולה→טאבולה, punctuation)
- [ ] **Smart Domain STT** (HR/Product prompts)
- [x] **Visual-to-Code** (Copy JSON button)
- [ ] **Deep Link Sharing** (timestamp jumps)

---

## ⭐ PRIORITY 2 (Week 2)

- [ ] **ADRs Auto-Generator** (Spec upgrade 1)
- [ ] **GitHub Repo RAG** (Spec upgrade 2)
- [ ] **Real Jira Sync**
- [ ] **Advanced OCR**

---

## 🎯 PRIORITY 3 (Month)

- [ ] **Real Calendar API** (Google Calendar / Outlook)
- [ ] **Speaker Diarization** (pyannote.audio)
- [ ] **Local-First Mode** (Ollama / on-prem LLMs)
- [ ] **MCP Server** (Agent Connectivity)

---

## 🌐 Future Vision: Q2 2026+

- [ ] **Advanced RAG on Organizational Docs**
  - Entity linking (components, services, projects)
  - Session JSON + docs as "experience corpus"
- [ ] **Self-Improving Memory Loop**
  - Learn from past sessions and refine prompts
- [ ] **Full Async Processing**
  - Celery + Redis background worker queue
- [ ] **Expanded Integrations**
  - Slack (push summaries + links)
  - Confluence / GitHub Wikis
  - Alternative AI engines (Claude 3.5 Sonnet, etc.)
