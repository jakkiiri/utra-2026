from pydantic import BaseModel
from typing import Optional, List
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


class WebSocketMessage(BaseModel):
    type: WebSocketEventType
    data: dict = {}
