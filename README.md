# WinterStream AI 🏂❄️

An accessibility-first, audio-centric Winter Olympics companion web application. This app allows users to watch Winter Olympics events while receiving AI-powered accessible commentary and the ability to ask questions about what's happening.

## Features

- **YouTube Video Integration**: Paste any YouTube video or livestream URL
- **Automatic Transcript Retrieval**: Fetches video captions for context
- **AI-Powered Q&A**: Ask questions about the event using Gemini AI
- **Text-to-Speech Responses**: Answers are read aloud using ElevenLabs
- **Voice Input**: Ask questions by speaking (auto-pauses video)
- **Accessibility First**: Designed for blind/visually impaired users and sports newcomers

## Tech Stack

### Frontend
- **Next.js 16** with React 19
- **TypeScript**
- **Tailwind CSS** for styling
- **YouTube IFrame API** for video playback
- **Web Speech API** for voice input

### Backend
- **FastAPI** (Python)
- **WebSockets** for real-time communication
- **Google Gemini API** for AI reasoning
- **ElevenLabs API** for text-to-speech
- **YouTube Transcript API** for caption retrieval

## Project Structure

```
utra-2026/
├── frontend/                 # Next.js frontend
│   ├── app/                  # App router pages
│   ├── components/           # React components
│   │   ├── video-player.tsx      # YouTube player with IFrame API
│   │   ├── video-url-input.tsx   # URL input component
│   │   ├── ai-chat-input.tsx     # Chat input with voice support
│   │   ├── ai-commentary.tsx     # Commentary feed sidebar
│   │   ├── stream-header.tsx     # Header component
│   │   └── event-sidebar.tsx     # Event info sidebar
│   └── lib/                  # Utilities
│       ├── api.ts                # API client & WebSocket
│       └── youtube.ts            # YouTube IFrame utilities
│
└── backend/                  # FastAPI backend
    ├── main.py               # Main FastAPI application
    ├── config.py             # Configuration & env vars
    ├── models.py             # Pydantic models
    ├── requirements.txt      # Python dependencies
    ├── key.env               # API keys (not committed)
    └── services/             # Service modules
        ├── youtube_service.py    # YouTube transcript handling
        ├── gemini_service.py     # Gemini AI integration
        └── elevenlabs_service.py # Text-to-speech integration
```

## Setup Instructions

### Prerequisites
- Node.js 18+ 
- Python 3.10+
- Gemini API key
- ElevenLabs API key

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure API keys in `key.env`:
   ```
   gemini_api_key=your_gemini_api_key_here
   elevenlabs_api_key=your_elevenlabs_api_key_here
   ```

5. Start the backend server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. (Optional) Configure environment variables:
   ```bash
   cp .env.local.example .env.local
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

5. Open [http://localhost:3000](http://localhost:3000) in your browser

## Usage

1. **Load a Video**: Paste a YouTube video or livestream URL in the input field
2. **Watch**: The video will play in the background with controls
3. **Ask Questions**: 
   - Type your question in the chat input
   - Or click the microphone button to ask by voice
   - The video will auto-pause when you start speaking
4. **Get Answers**: AI will respond with accessible explanations, both in text and audio

## API Endpoints

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/video/load` | POST | Load a YouTube video and fetch transcript |
| `/question` | POST | Ask a question about the current video |
| `/transcript/{video_id}` | GET | Get transcript for a video |
| `/audio/{audio_id}` | GET | Retrieve generated audio |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `/ws/events` | Real-time events (questions, responses, pause) |
| `/ws/transcript` | Live transcript streaming |

## Accessibility Features

- **No Visual References**: AI avoids phrases like "as you can see"
- **Descriptive Audio**: All responses are converted to clear speech
- **Voice Input**: No keyboard required for questions
- **Auto-Pause**: Video pauses when you speak
- **Screen Reader Support**: ARIA labels and live regions
- **Beginner-Friendly**: Explanations assume no prior sports knowledge

## License

MIT License - Built for UTRA 2026 Hackathon
