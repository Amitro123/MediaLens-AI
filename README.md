# 📺 MediaLens AI

**Turn broadcast content into searchable intelligence.**

MediaLens adapts the powerful video analysis engine of DevLens for the media and entertainment industry. It uses Gemini 2.0 Flash to process TV episodes, news segments, and raw footage—turning them into structured, searchable data.

## 🚀 Key Features

### 🎬 Scene Detection & Cataloging
- **Granular Segmentation**: Automatically breaks episodes into scenes.
- **Visual Analysis**: Detects objects, locations, and actions (e.g., "sunglasses", "living room", "argument").
- **Dialogue Transcription**: Perfect Hebrew/English transcription with speaker identification.
- **Keyword Indexing**: specific visual and thematic elements.

### ✂️ Viral Clip Generator
- **Social Media Ready**: Identifies funny, dramatic, or viral moments.
- **Smart Cropping**: (Planned) Auto-reframes for vertical (9:16) viewing.
- **Hook Extraction**: Suggests captions and hashtags for TikTok/Reels.

### 👤 Character Tracker
- **Appearance Timeline**: Track where specific characters appear.
- **Action Tracking**: "Find all scenes where Hefer is driving."
- **Outfit Analysis**: Track costume changes across an episode.

## 🛠️ Architecture

- **Backend**: FastAPI + Python
- **AI Models**: Google Gemini 2.0 Flash (Vision + Audio + Text)
- **Frontend**: React + Vite + TailwindCSS
- **Storage**: Redis (Processing Queue) + Local Storage (Artifacts)

## 🏃‍♂️ Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (Optional)
- Google Gemini API Key

### Installation

1. **Clone & Setup**
   ```bash
   git clone https://github.com/Amitro123/MediaLens-AI.git
   cd MediaLens-AI
   cp .env.example .env
   # Add your GEMINI_API_KEY to .env
   ```

2. **Start Backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   python run.py
   ```

3. **Start Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## 🎯 Use Cases

- **Keshet/Reshet**: Quickly find archival footage for promos.
- **News Rooms**: Search raw feeds for specific politicians or events.
- **Reality TV**: track contestant interactions and storylines.
- **Social Media Teams**: Auto-generate daily content clips.

## 📄 License
MIT License
