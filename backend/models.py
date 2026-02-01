from pydantic import BaseModel, Field
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


# =============================================================================
# Structured Output Schemas for LangChain
# =============================================================================

class PlayerStatistic(BaseModel):
    """Individual player statistic"""
    label: str = Field(description="Stat label (e.g., 'Record', 'Championships', 'Win Rate')")
    value: str = Field(description="Stat value (e.g., '29-0', '3 titles', '85%')")


class PlayerProfile(BaseModel):
    """Structured player profile extracted from search results"""
    name: str = Field(description="Player's full name")
    sport: str = Field(description="Sport or discipline (e.g., 'MMA', 'Snowboarding')")
    summary: str = Field(description="Concise 1-2 sentence summary of player's career and achievements")
    key_stats: List[PlayerStatistic] = Field(
        description="3-5 most important statistics or achievements",
        max_length=5
    )
    notable_achievement: str = Field(description="Single most notable achievement or record")
    source_url: Optional[str] = Field(description="URL of primary source")
    image_url: Optional[str] = Field(description="URL of player image if available")


class EventContext(BaseModel):
    """Structured event/competition context"""
    event_name: str = Field(description="Name of the event or competition")
    sport: str = Field(description="Sport or discipline")
    key_facts: List[str] = Field(
        description="2-4 key facts about the event, rules, or history",
        max_length=4
    )
    significance: str = Field(description="Why this event is significant or interesting")
    source_url: Optional[str] = Field(description="URL of primary source")
