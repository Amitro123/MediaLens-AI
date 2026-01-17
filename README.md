# 📺 MediaLens AI

**Turn broadcast content into searchable intelligence.**

MediaLens empowers broadcasters and production teams to instantly search, analyze, and repurpose video content using advanced Multimodal AI. Optimized for Hebrew content with specialized support for "Hebrish" (Hebrew + English) transcription.

## 🚀 Key Features

### 🎬 Scene Detection & Cataloging
- **Smart Segmentation**: Automatically breaks episodes into logical scenes based on visual and audio cues.
- **Deep Search**: Find "all scenes with Hefer wearing sunglasses" or "scenes discussing budget in the kitchen".
- **Visual & Audio Indexing**: Catalog locations, objects, actions, and spoken dialogue.

### ✂️ Viral Clip Generator
- **Auto-Discovery**: Identifies funny, dramatic, or high-engagement moments perfect for social media.
- **Physical Generation**: Automatically cuts and exports **9:16 vertical clips** ready for TikTok and Reels.
- **Social Metadata**: Suggests engaging captions, hooks, and hashtags for each clip.

### 🗣️ "Hebrish" Transcription (New)
- **Specialized STT**: Built-in `faster-whisper` model fine-tuned for Israeli tech and casual speech (Hebrew + English code-switching).
- **Subtitle Export**: Generates time-synced SRT files automatically.

### 👤 Character & Action Tracker
- **Appearance Timelines**: Visual heatmaps of when characters appear.
- **Action Identification**: Track specific actions (e.g., "driving", "eating", "arguing").

## 🛠️ Architecture

- **Backend**: FastAPI + Python (Video Pipeline, FFmpeg, Whisper)
- **AI Core**: Google Gemini 2.0 Flash (Multimodal Understanding) + Faster-Whisper (Specialized STT)
- **Frontend**: React + Vite + TailwindCSS + Shadcn/UI
- **Storage**: Redis (Processing Queue) + Local Filesystem (Artifacts)

## 🏃‍♂️ Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- [FFmpeg](https://ffmpeg.org/download.html) installed and in system PATH
- Google Gemini API Key

### Installation

1. **Clone & Configuration**
   ```bash
   git clone https://github.com/Amitro123/MediaLens-AI.git
   cd MediaLens-AI
   # Create .env from example
   cp backend/.env.example backend/.env
   ```

2. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   
   # Enable Hebrish STT in .env
   # HEBRISH_STT_ENABLED=True
   
   python run.py
   # Server running at http://localhost:8000
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   # UI running at http://localhost:5173
   ```

## 🎯 Production Use Cases

- **Archive Search**: "Find the clip from 2018 where [Politician] mentions [Topic]."
- **Promo Creation**: Quickly gather all dramatic reactions for a season trailer.
- **Social Media Automation**: Turn a 1-hour episode into 10 shareable vertical clips in minutes.
- **Accessibility**: Zero-effort accurate Hebrew subtitles.

## 📄 License
MIT License
