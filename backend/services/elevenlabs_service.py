import httpx
import base64
from typing import Optional
import uuid
import os

from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL_ID


class ElevenLabsService:
    """Service for handling ElevenLabs text-to-speech conversion."""
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    # In-memory audio storage (for MVP)
    _audio_cache: dict[str, bytes] = {}
    
    def __init__(self):
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
    
    async def text_to_speech(
        self, 
        text: str, 
        voice_id: str = ELEVENLABS_VOICE_ID
    ) -> Optional[str]:
        """
        Convert text to speech using ElevenLabs API.
        
        Args:
            text: The text to convert to speech
            voice_id: The voice ID to use
            
        Returns:
            Audio ID that can be used to retrieve the audio, or None on failure
        """
        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"
        
        payload = {
            "text": text,
            "model_id": ELEVENLABS_MODEL_ID,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    audio_id = str(uuid.uuid4())
                    self._audio_cache[audio_id] = response.content
                    return audio_id
                else:
                    print(f"ElevenLabs API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"ElevenLabs request error: {e}")
            return None
    
    def get_audio(self, audio_id: str) -> Optional[bytes]:
        """Retrieve cached audio by ID."""
        return self._audio_cache.get(audio_id)
    
    def get_audio_base64(self, audio_id: str) -> Optional[str]:
        """Get audio as base64-encoded string for WebSocket transmission."""
        audio_bytes = self._audio_cache.get(audio_id)
        if audio_bytes:
            return base64.b64encode(audio_bytes).decode('utf-8')
        return None
    
    def clear_audio(self, audio_id: str):
        """Remove audio from cache to free memory."""
        if audio_id in self._audio_cache:
            del self._audio_cache[audio_id]
    
    async def get_available_voices(self) -> list:
        """Get list of available voices from ElevenLabs."""
        url = f"{self.BASE_URL}/voices"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"xi-api-key": ELEVENLABS_API_KEY},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [
                        {"voice_id": v["voice_id"], "name": v["name"]}
                        for v in data.get("voices", [])
                    ]
        except Exception as e:
            print(f"Error fetching voices: {e}")
        
        return []


# Singleton instance
elevenlabs_service = ElevenLabsService()
