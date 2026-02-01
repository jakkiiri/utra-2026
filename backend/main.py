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
from contextlib import asynccontextmanager

from config import TRANSCRIPT_WINDOW_SECONDS
from models import (
    VideoLoadRequest,
    VideoLoadResponse,
    QuestionRequest,
    QuestionResponse,
    TranscriptEntry,
    WebSocketEventType,
    WebSocketMessage,
    CommentaryItemPush,
)
from services.youtube_service import YouTubeService
from services.gemini_service import gemini_service
from services.elevenlabs_service import elevenlabs_service
from services.agent_service import agent_service
# from services.screenshot_service import capture_youtube_frame  # Disabled: YouTube blocks bots


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🏂 WinterStream AI API started")
    print("📡 WebSocket endpoints ready at /ws/events and /ws/transcript")
    yield


# Initialize FastAPI app
app = FastAPI(
    title="WinterStream AI API",
    description="Backend API for accessibility-first Winter Olympics companion app",
    version="1.0.0",
    lifespan=lifespan
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
# Helper Functions
# =============================================================================

async def push_exa_result_as_card(exa_result: dict, is_player: bool = False):
    """
    Push an Exa search result as a commentary card to all connected clients.

    Args:
        exa_result: Dictionary with title, url, highlights, score, image (optional)
        is_player: Whether this is a player/athlete profile (enables special formatting)
    """
    # Extract content from highlights
    highlights = exa_result.get("highlights", [])
    if isinstance(highlights, str):
        highlights = [highlights]

    title = exa_result.get("title", "Search Result")

    # Detect if this is a player profile
    player_keywords = ["fighter", "athlete", "player", "ufc", "boxer", "wrestler", "champion"]
    is_player_profile = is_player or any(keyword in title.lower() for keyword in player_keywords)

    if is_player_profile:
        # Format as player profile card with stats
        card = CommentaryItemPush(
            type="player_profile",
            title=title,
            content=highlights[0] if highlights else "Professional athlete profile",
            highlight={
                "value": exa_result.get("url", ""),
                "label": "Full Profile",
                "image": exa_result.get("image", ""),  # Player image from Exa
                "stats": highlights[1:4] if len(highlights) > 1 else []  # Stats bullets
            }
        )
    else:
        # Regular info card
        content = highlights[0] if highlights else ""
        card = CommentaryItemPush(
            type="historical",
            title=title,
            content=content or "Click source to learn more",
            highlight={
                "value": exa_result.get("url", ""),
                "label": "Source"
            }
        )

    await manager.broadcast(
        WebSocketMessage(
            type=WebSocketEventType.PUSH_COMMENTARY,
            data=card.model_dump()
        )
    )


async def research_video_context_background(video_id: str, video_title: str):
    """
    Background task: Research players and event info when video loads.
    Pushes results as cards automatically.

    Args:
        video_id: YouTube video ID
        video_title: Video title for context
    """
    try:
        print(f"🔍 Starting proactive research for: {video_title}")

        # Use agent service to research
        context = await agent_service.research_video_context(
            video_title=video_title
        )

        # Push player info cards
        for player_info in context.get("players", []):
            if player_info.get("info"):
                info = player_info["info"]
                highlights = info.get("highlights", [])
                content = highlights[0] if highlights else "Player information available"

                card = CommentaryItemPush(
                    type="analysis",
                    title=f"Player: {player_info['name']}",
                    content=content,
                    highlight={
                        "value": info.get("url", ""),
                        "label": "Source"
                    }
                )

                await manager.broadcast(
                    WebSocketMessage(
                        type=WebSocketEventType.PUSH_COMMENTARY,
                        data=card.model_dump()
                    )
                )

                # Small delay between cards to avoid flooding
                await asyncio.sleep(0.5)

        # Push event context card
        event_info = context.get("event_info")
        if event_info:
            highlights = event_info.get("highlights", [])
            content = highlights[0] if highlights else "Event information available"

            card = CommentaryItemPush(
                type="historical",
                title=f"About {context.get('sport', 'this event')}",
                content=content,
                highlight={
                    "value": event_info.get("url", ""),
                    "label": "Source"
                }
            )

            await manager.broadcast(
                WebSocketMessage(
                    type=WebSocketEventType.PUSH_COMMENTARY,
                    data=card.model_dump()
                )
            )

        print(f"✅ Proactive research complete for: {video_title}")

    except Exception as e:
        print(f"❌ Proactive research failed: {e}")


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
    5. Triggers proactive research in background (players, event info)
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

    # Trigger proactive research in background
    video_title = metadata.get("title", "Unknown")
    asyncio.create_task(
        research_video_context_background(video_id, video_title)
    )

    return VideoLoadResponse(
        video_id=video_id,
        title=video_title,
        is_live=is_live,
        has_captions=has_captions,
        message=message
    )


@app.post("/question", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Process a user question about the current video using agentic approach.

    This endpoint:
    1. Uses LangChain agent with tool access (Exa search, screenshot analysis, transcript)
    2. Generates an accessibility-friendly answer
    3. Converts the answer to speech using ElevenLabs
    4. Pushes any Exa search results as cards
    5. Returns both text and audio response
    """
    # Notify clients that processing started
    await manager.broadcast(WebSocketMessage(
        type=WebSocketEventType.PROCESSING_START,
        data={}
    ))

    try:
        # Use agent service with tool access
        result = await agent_service.answer_question(
            question=request.question,
            video_id=request.video_id,
            playback_time=request.playback_time,
            screenshot_base64=request.screenshot
        )

        answer = result["answer"]
        exa_results = result.get("exa_results", [])
        tools_used = result.get("tools_used", [])

        # NOTE: Cards are now pushed by the agent itself using push_info_card tool
        # The agent processes and summarizes information before pushing cards
        # No automatic card pushing to avoid dumping raw, unorganized data

        # Convert answer to speech
        audio_id = await elevenlabs_service.text_to_speech(answer)
        audio_url = f"/audio/{audio_id}" if audio_id else None

        # Get transcript for response
        transcript_context = YouTubeService.get_transcript_window(
            request.video_id,
            request.playback_time,
            TRANSCRIPT_WINDOW_SECONDS
        )

        # Broadcast completion
        await manager.broadcast(WebSocketMessage(
            type=WebSocketEventType.PROCESSING_COMPLETE,
            data={"tools_used": tools_used}
        ))

        return QuestionResponse(
            answer=answer,
            audio_url=audio_url,
            transcript_context=transcript_context
        )

    except Exception as e:
        await manager.broadcast(WebSocketMessage(
            type=WebSocketEventType.ERROR,
            data={"message": str(e)}
        ))
        raise HTTPException(status_code=500, detail=str(e))


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


# DISABLED: YouTube blocks server-side screenshot capture (Error 153 bot detection)
# Even with Playwright stealth mode, YouTube detects automation and shows error page
# Alternative: Frontend Screen Capture API (requires user permission each time)
# Current solution: Agent works without screenshots using transcript + metadata + Exa search

# @app.get("/screenshot/{video_id}/{timestamp}")
# async def get_screenshot(video_id: str, timestamp: float):
#     """
#     Capture a screenshot from a YouTube video at the specified timestamp.
#     Uses server-side rendering to bypass CORS restrictions.
#
#     Returns base64 encoded JPEG image.
#     """
#     try:
#         screenshot_base64 = await capture_youtube_frame(video_id, timestamp)
#
#         if not screenshot_base64:
#             raise HTTPException(
#                 status_code=500,
#                 detail="Failed to capture screenshot"
#             )
#
#         return {"screenshot": screenshot_base64}
#
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Screenshot capture error: {str(e)}"
#         )


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


@app.post("/commentary/push")
async def push_commentary(item: CommentaryItemPush):
    """
    Push a commentary item to all connected clients.

    This allows the AI to proactively send insights without user questions.
    Useful for:
    - Live event updates
    - Automatic historical comparisons
    - Critical moment annotations
    """
    import time
    from datetime import datetime

    # Auto-generate ID if not provided
    if not item.id:
        item.id = f"push-{int(time.time() * 1000)}"

    # Auto-generate timestamp if not provided
    if not item.timestamp:
        item.timestamp = datetime.now().strftime("%H:%M:%S")

    # Broadcast to all connected WebSocket clients
    await manager.broadcast(
        WebSocketMessage(
            type=WebSocketEventType.PUSH_COMMENTARY,
            data=item.model_dump()
        )
    )

    return {"status": "success", "commentary_id": item.id}


@app.post("/event/update")
async def push_event_update(update: dict):
    """
    Push event sidebar updates (win probability, technical scores, etc.)

    Example payload:
    {
        "winProbability": 65,
        "probabilityChange": +5,
        "technicalScore": 92.5,
        "riskWarning": {
            "title": "High Risk",
            "description": "Difficult landing ahead",
            "probability": 15
        }
    }
    """
    await manager.broadcast(
        WebSocketMessage(
            type=WebSocketEventType.PUSH_EVENT_UPDATE,
            data=update
        )
    )

    return {"status": "success"}


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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
