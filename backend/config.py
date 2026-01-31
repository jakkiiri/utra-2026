import os
from dotenv import load_dotenv

# Load environment variables from key.env
load_dotenv("key.env")

# API Keys
GEMINI_API_KEY = os.getenv("gemini_api_key")
ELEVENLABS_API_KEY = os.getenv("elevenlabs_api_key")

# ElevenLabs settings
ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel - clear, friendly voice
ELEVENLABS_MODEL_ID = "eleven_turbo_v2_5"  # Updated model for free tier

# Transcript settings
TRANSCRIPT_WINDOW_SECONDS = 30  # How many seconds of transcript context to provide

# Validate required keys
if not GEMINI_API_KEY:
    raise ValueError("Missing gemini_api_key in key.env")
if not ELEVENLABS_API_KEY:
    raise ValueError("Missing elevenlabs_api_key in key.env")
