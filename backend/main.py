"""
WinterStream AI - Backend API
An accessibility-first Winter Olympics companion app.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import List, Set
import json
import asyncio

from config import TRANSCRIPT_WINDOW_SECONDS
from models import (
    VideoLoadRequest,
    VideoLoadResponse,
    QuestionRequest,
    QuestionResponse,
    TranscriptEntry,
    WebSocketEventType,
    WebSocketMessage,
)
from services.youtube_service import YouTubeService
from services.gemini_service import gemini_service
from services.elevenlabs_service import elevenlabs_service


# Initialize FastAPI app
app = FastAPI(
    title="WinterStream AI API",
    description="Backend API for accessibility-first Winter Olympics companion app",
    version="1.0.0"
)

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        print(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_message(self, websocket: WebSocket, message: WebSocketMessage):
        try:
            await websocket.send_json(message.model_dump())
        except Exception as e:
            print(f"Error sending WebSocket message: {e}")
    
    async def broadcast(self, message: WebSocketMessage):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message.model_dump())
            except Exception:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.active_connections.discard(conn)


manager = ConnectionManager()


# =============================================================================
# REST API Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "WinterStream AI API"}


@app.post("/video/load", response_model=VideoLoadResponse)
async def load_video(request: VideoLoadRequest):
    """
    Load a YouTube video and fetch its transcript.
    
    This endpoint:
    1. Extracts the video ID from the URL
    2. Fetches video metadata
    3. Attempts to retrieve captions/transcript
    4. Stores transcript for future queries
    """
    video_id = YouTubeService.extract_video_id(request.url)
    
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Please provide a valid video or livestream URL."
        )
    
    # Fetch video metadata
    metadata = await YouTubeService.get_video_metadata(video_id)
    
    # Fetch transcript
    transcript, has_captions = YouTubeService.fetch_transcript(video_id)
    
    # Check if this might be a live stream (no transcript typically means live)
    is_live = not has_captions and len(transcript) == 0
    
    message = ""
    if has_captions:
        message = f"Loaded video with {len(transcript)} transcript segments."
    elif is_live:
        message = "Live stream detected. Transcript will be generated in real-time."
    else:
        message = "No captions available. Using video title and description for context."
    
    return VideoLoadResponse(
        video_id=video_id,
        title=metadata.get("title", "Unknown"),
        is_live=is_live,
        has_captions=has_captions,
        message=message
    )


@app.post("/question", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Process a user question about the current video.
    
    This endpoint:
    1. Retrieves relevant context (transcript or video metadata)
    2. Uses Gemini to generate an accessibility-friendly answer
    3. Converts the answer to speech using ElevenLabs
    4. Returns both text and audio response
    """
    # Get context - uses transcript if available, falls back to video metadata
    context_text = YouTubeService.get_context_text(
        request.video_id,
        request.playback_time
    )
    
    # Get transcript for response (may be empty)
    transcript_context = YouTubeService.get_transcript_window(
        request.video_id,
        request.playback_time,
        TRANSCRIPT_WINDOW_SECONDS
    )
    
    # Generate answer using Gemini with context (transcript or metadata)
    answer = await gemini_service.answer_question(
        question=request.question,
        context_text=context_text,
        sport_type="Winter Olympics event"
    )
    
    # Convert answer to speech
    audio_id = await elevenlabs_service.text_to_speech(answer)
    
    # Build audio URL if generation was successful
    audio_url = f"/audio/{audio_id}" if audio_id else None
    
    return QuestionResponse(
        answer=answer,
        audio_url=audio_url,
        transcript_context=transcript_context
    )


@app.get("/transcript/{video_id}")
async def get_transcript(
    video_id: str,
    start_time: float = 0,
    end_time: float = None
):
    """
    Get transcript for a video, optionally filtered by time range.
    
    Args:
        video_id: YouTube video ID
        start_time: Start of time range (seconds)
        end_time: End of time range (seconds), None for full transcript
    """
    transcript = YouTubeService.get_full_transcript(video_id)
    
    if not transcript:
        raise HTTPException(
            status_code=404,
            detail="Transcript not found. Please load the video first."
        )
    
    # Filter by time range if end_time is specified
    if end_time is not None:
        transcript = [
            entry for entry in transcript
            if start_time <= entry.start <= end_time
        ]
    
    return {
        "video_id": video_id,
        "entries": [entry.model_dump() for entry in transcript],
        "total_entries": len(transcript)
    }


@app.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """
    Retrieve generated audio by ID.
    
    Returns MP3 audio data for playback.
    """
    audio_data = elevenlabs_service.get_audio(audio_id)
    
    if not audio_data:
        raise HTTPException(
            status_code=404,
            detail="Audio not found or expired."
        )
    
    return Response(
        content=audio_data,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"inline; filename={audio_id}.mp3"
        }
    )


# =============================================================================
# WebSocket Endpoints
# =============================================================================

@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """
    WebSocket endpoint for real-time events.
    
    Handles:
    - Client connection/disconnection
    - Voice detection notifications
    - Real-time transcript updates
    - Audio response streaming
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            event_type = message.get("type")
            event_data = message.get("data", {})
            
            if event_type == "VOICE_DETECTED":
                # User started speaking - notify to pause video
                await manager.send_message(
                    websocket,
                    WebSocketMessage(
                        type=WebSocketEventType.PAUSE_VIDEO,
                        data={"reason": "voice_input"}
                    )
                )
            
            elif event_type == "PLAYBACK_UPDATE":
                # Client is sending playback position updates
                # Could be used for live transcript sync
                video_id = event_data.get("video_id")
                playback_time = event_data.get("playback_time")
                # Store or process as needed
            
            elif event_type == "QUESTION":
                # Process question via WebSocket for real-time response
                await manager.send_message(
                    websocket,
                    WebSocketMessage(
                        type=WebSocketEventType.PROCESSING_START,
                        data={}
                    )
                )
                
                try:
                    # Get context (transcript or video metadata)
                    video_id = event_data.get("video_id", "")
                    playback_time = event_data.get("playback_time", 0)
                    question = event_data.get("question", "")
                    
                    context_text = YouTubeService.get_context_text(
                        video_id, playback_time
                    )
                    
                    # Generate answer
                    answer = await gemini_service.answer_question(
                        question=question,
                        context_text=context_text
                    )
                    
                    # Generate audio
                    audio_id = await elevenlabs_service.text_to_speech(answer)
                    audio_base64 = None
                    if audio_id:
                        audio_base64 = elevenlabs_service.get_audio_base64(audio_id)
                    
                    # Send response
                    await manager.send_message(
                        websocket,
                        WebSocketMessage(
                            type=WebSocketEventType.AUDIO_RESPONSE,
                            data={
                                "answer": answer,
                                "audio_base64": audio_base64,
                                "audio_url": f"/audio/{audio_id}" if audio_id else None
                            }
                        )
                    )
                    
                except Exception as e:
                    await manager.send_message(
                        websocket,
                        WebSocketMessage(
                            type=WebSocketEventType.ERROR,
                            data={"message": str(e)}
                        )
                    )
                
                finally:
                    await manager.send_message(
                        websocket,
                        WebSocketMessage(
                            type=WebSocketEventType.PROCESSING_COMPLETE,
                            data={}
                        )
                    )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.websocket("/ws/transcript")
async def websocket_transcript(websocket: WebSocket):
    """
    WebSocket endpoint for real-time transcript streaming.
    
    Used for live streams where transcript is generated in real-time.
    """
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "LIVE_TRANSCRIPT":
                # Store incoming live transcript entry
                video_id = message.get("video_id")
                entry_data = message.get("entry", {})
                
                if video_id and entry_data:
                    entry = TranscriptEntry(
                        start=entry_data.get("start", 0),
                        duration=entry_data.get("duration", 0),
                        text=entry_data.get("text", "")
                    )
                    YouTubeService.add_live_transcript_entry(video_id, entry)
                    
                    # Broadcast transcript update to all clients
                    await manager.broadcast(
                        WebSocketMessage(
                            type=WebSocketEventType.TRANSCRIPT_UPDATE,
                            data={"entry": entry.model_dump()}
                        )
                    )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Transcript WebSocket error: {e}")
        manager.disconnect(websocket)


# =============================================================================
# Application Startup
# =============================================================================

@app.on_event("startup")
async def startup_event():
    print("🏂 WinterStream AI API started")
    print("📡 WebSocket endpoints ready at /ws/events and /ws/transcript")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
