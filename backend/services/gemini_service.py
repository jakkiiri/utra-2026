from google import genai
from typing import List
import os

from config import GEMINI_API_KEY
from models import TranscriptEntry


# System prompt for accessibility-first sports commentary
SYSTEM_PROMPT = """You are a friendly, casual sports companion helping someone watch the Winter Olympics.

RESPOND IN 2-3 SHORT SENTENCES MAXIMUM. Be brief and conversational like texting a friend.

Key rules:
- Keep it SHORT - this is a live event, don't make them miss action
- Be warm and casual, like a friend explaining the sport
- Never say "as you can see" or visual references
- If explaining rules, give the simplest version
- Sound natural - your response will be read aloud

Example good responses:
- "That's a triple axel! It's one of the hardest jumps - they spin 3.5 times in the air. Pretty impressive stuff!"
- "She's in first place right now with a score of 85. That's really solid for the short program."
- "Curling is basically shuffleboard on ice. They slide stones trying to get closest to the center target."

Keep answers friendly, brief, and helpful!"""


class GeminiService:
    """Service for handling Gemini AI interactions."""
    
    def __init__(self):
        # Initialize the new Google GenAI client
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = "gemini-2.0-flash"  # Current available model
    
    def format_transcript_context(self, entries: List[TranscriptEntry]) -> str:
        """Format transcript entries into a readable context string."""
        if not entries:
            return "No recent commentary available."
        
        formatted = []
        for entry in entries:
            minutes = int(entry.start // 60)
            seconds = int(entry.start % 60)
            formatted.append(f"[{minutes}:{seconds:02d}] {entry.text}")
        
        return "\n".join(formatted)
    
    async def answer_question(
        self, 
        question: str, 
        context_text: str,
        sport_type: str = "Winter Olympics event"
    ) -> str:
        """
        Generate an accessibility-friendly answer to a user's question.
        
        Args:
            question: The user's question
            context_text: Context about the video (transcript or metadata)
            sport_type: The type of sport being watched
            
        Returns:
            The generated answer text
        """
        prompt = f"""{SYSTEM_PROMPT}

Context: {sport_type}
{context_text}

Question: {question}

Answer briefly (2-3 sentences max):"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            if response.text:
                return response.text.strip()
            else:
                return "I apologize, but I couldn't generate a response. Could you please rephrase your question?"
                
        except Exception as e:
            print(f"Gemini API error: {e}")
            return "I'm having trouble processing your question right now. Please try again in a moment."
    
    async def generate_sport_explanation(self, sport_name: str) -> str:
        """Generate a beginner-friendly explanation of a Winter Olympic sport."""
        prompt = f"""{SYSTEM_PROMPT}

Please provide a brief, accessible introduction to {sport_name} for someone who has never watched this sport before. 
Include:
1. What the basic goal of the sport is
2. How scoring or competition works
3. Key things to listen for during commentary
4. What makes a performance impressive

Keep it concise and conversational - this will be read aloud."""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            if response.text:
                return response.text.strip()
            return f"Let me tell you about {sport_name}..."
        except Exception as e:
            print(f"Gemini API error: {e}")
            return f"I'd love to tell you about {sport_name}, but I'm having some technical difficulties."


# Singleton instance
gemini_service = GeminiService()
