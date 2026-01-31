import re
from typing import Optional, List, Tuple
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import httpx

from models import TranscriptEntry


class YouTubeService:
    """Service for handling YouTube video operations and transcript retrieval."""
    
    # In-memory storage (for MVP - would use Redis in production)
    _transcripts: dict[str, List[TranscriptEntry]] = {}
    _video_metadata: dict[str, dict] = {}
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/live\/([a-zA-Z0-9_-]{11})',
            r'^([a-zA-Z0-9_-]{11})$'  # Just the ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @classmethod
    async def get_video_metadata(cls, video_id: str) -> dict:
        """Get video metadata using oEmbed API and scraping (no API key required)."""
        metadata = {
            "video_id": video_id,
            "title": "Winter Olympics Event",
            "author": "Unknown",
            "description": "",
            "thumbnail": ""
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Get basic info from oEmbed
                response = await client.get(
                    f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json",
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    metadata["title"] = data.get("title", "Unknown Title")
                    metadata["author"] = data.get("author_name", "Unknown")
                    metadata["thumbnail"] = data.get("thumbnail_url", "")
                
                # Try to get description from page (basic scraping)
                try:
                    page_response = await client.get(
                        f"https://www.youtube.com/watch?v={video_id}",
                        timeout=10.0,
                        headers={"User-Agent": "Mozilla/5.0"}
                    )
                    if page_response.status_code == 200:
                        content = page_response.text
                        # Extract description from meta tag
                        desc_match = re.search(r'<meta name="description" content="([^"]*)"', content)
                        if desc_match:
                            metadata["description"] = desc_match.group(1)
                except Exception as e:
                    print(f"Could not fetch video description: {e}")
                    
        except Exception as e:
            print(f"Error fetching video metadata: {e}")
        
        # Store metadata for later use
        cls._video_metadata[video_id] = metadata
        return metadata
    
    @classmethod
    def get_stored_metadata(cls, video_id: str) -> dict:
        """Get stored metadata for a video."""
        return cls._video_metadata.get(video_id, {})
    
    @classmethod
    def get_context_text(cls, video_id: str, current_time: float = 0) -> str:
        """
        Get context text for AI - uses transcript if available, 
        otherwise falls back to video metadata.
        """
        # First try to get transcript context
        transcript_entries = cls.get_transcript_window(video_id, current_time, 30.0)
        
        if transcript_entries:
            formatted = []
            for entry in transcript_entries:
                minutes = int(entry.start // 60)
                seconds = int(entry.start % 60)
                formatted.append(f"[{minutes}:{seconds:02d}] {entry.text}")
            return "Recent commentary transcript:\n" + "\n".join(formatted)
        
        # Fall back to metadata
        metadata = cls._video_metadata.get(video_id, {})
        if metadata:
            context_parts = []
            if metadata.get("title"):
                context_parts.append(f"Video Title: {metadata['title']}")
            if metadata.get("author"):
                context_parts.append(f"Channel: {metadata['author']}")
            if metadata.get("description"):
                context_parts.append(f"Description: {metadata['description']}")
            
            if context_parts:
                return "Video information (no transcript available):\n" + "\n".join(context_parts)
        
        return "No transcript or video information available."
    
    @classmethod
    def fetch_transcript(cls, video_id: str) -> Tuple[List[TranscriptEntry], bool]:
        """
        Fetch transcript for a video.
        Returns tuple of (transcript_entries, has_captions).
        """
        try:
            # Try to get transcript (prefers manual captions, falls back to auto-generated)
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to find English transcript
            transcript = None
            for t in transcript_list:
                if t.language_code.startswith('en'):
                    transcript = t.fetch()
                    break
            
            # If no English, try to get any transcript and translate
            if transcript is None:
                try:
                    transcript = transcript_list.find_generated_transcript(['en']).fetch()
                except:
                    # Get first available and translate
                    for t in transcript_list:
                        try:
                            transcript = t.translate('en').fetch()
                            break
                        except:
                            continue
            
            if transcript:
                entries = [
                    TranscriptEntry(
                        start=item['start'],
                        duration=item['duration'],
                        text=item['text']
                    )
                    for item in transcript
                ]
                cls._transcripts[video_id] = entries
                return entries, True
            
            return [], False
            
        except TranscriptsDisabled:
            print(f"Transcripts are disabled for video {video_id}")
            return [], False
        except NoTranscriptFound:
            print(f"No transcript found for video {video_id}")
            return [], False
        except Exception as e:
            print(f"Error fetching transcript: {e}")
            return [], False
    
    @classmethod
    def get_transcript_window(
        cls, 
        video_id: str, 
        current_time: float, 
        window_seconds: float = 30.0
    ) -> List[TranscriptEntry]:
        """
        Get transcript entries within a time window.
        Returns entries from [current_time - window_seconds, current_time].
        """
        transcript = cls._transcripts.get(video_id, [])
        if not transcript:
            return []
        
        start_time = max(0, current_time - window_seconds)
        end_time = current_time
        
        return [
            entry for entry in transcript
            if start_time <= entry.start <= end_time or
               (entry.start <= start_time and entry.start + entry.duration >= start_time)
        ]
    
    @classmethod
    def get_full_transcript(cls, video_id: str) -> List[TranscriptEntry]:
        """Get the full transcript for a video."""
        return cls._transcripts.get(video_id, [])
    
    @classmethod
    def store_transcript(cls, video_id: str, entries: List[TranscriptEntry]):
        """Store transcript entries for a video."""
        cls._transcripts[video_id] = entries
    
    @classmethod
    def add_live_transcript_entry(cls, video_id: str, entry: TranscriptEntry):
        """Add a new transcript entry for live streams."""
        if video_id not in cls._transcripts:
            cls._transcripts[video_id] = []
        cls._transcripts[video_id].append(entry)
