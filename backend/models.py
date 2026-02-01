from pydantic import BaseModel
from typing import Optional, List, Literal
from enum import Enum


class VideoLoadRequest(BaseModel):
    url: str


class VideoLoadResponse(BaseModel):
    video_id: str
    title: str
    is_live: bool
    has_captions: bool
    message: str


class TranscriptEntry(BaseModel):
    start: float  # Start time in seconds
    duration: float  # Duration in seconds
    text: str


class QuestionRequest(BaseModel):
    question: str
    video_id: str
    playback_time: float  # Current playback position in seconds
    is_live: bool = False
    screenshot: Optional[str] = None  # Base64 encoded screenshot for visual context


class QuestionResponse(BaseModel):
    answer: str
    audio_url: Optional[str] = None
    transcript_context: List[TranscriptEntry]


class WebSocketEventType(str, Enum):
    PAUSE_VIDEO = "PAUSE_VIDEO"
    RESUME_VIDEO = "RESUME_VIDEO"
    AUDIO_RESPONSE = "AUDIO_RESPONSE"
    TRANSCRIPT_UPDATE = "TRANSCRIPT_UPDATE"
    PROCESSING_START = "PROCESSING_START"
    PROCESSING_COMPLETE = "PROCESSING_COMPLETE"
    ERROR = "ERROR"
    PUSH_COMMENTARY = "PUSH_COMMENTARY"
    PUSH_EVENT_UPDATE = "PUSH_EVENT_UPDATE"


class WebSocketMessage(BaseModel):
    type: WebSocketEventType
    data: dict = {}


class CommentaryItemPush(BaseModel):
    """Model for pushing commentary items to frontend"""
    id: Optional[str] = None  # Auto-generate if not provided
    type: Literal['market_shift', 'historical', 'analysis', 'narration', 'player_profile']
    timestamp: Optional[str] = None  # Auto-generate if not provided
    title: Optional[str] = None
    content: str
    highlight: Optional[dict] = None  # { value: str, label?: str, image?: str, stats?: list }
    comparison: Optional[dict] = None  # { current: float, record: float, note: str }
