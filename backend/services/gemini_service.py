from google import genai
from typing import List
import os

from config import GEMINI_API_KEY
from models import TranscriptEntry


# System prompt for accessibility-first sports commentary
SYSTEM_PROMPT = """You are an accessibility-first sports commentator assistant for the Winter Olympics. 
Your audience may include:
- Blind or visually impaired users who cannot see the video
- People who are new to Winter Olympic sports and unfamiliar with the rules

CRITICAL GUIDELINES:
1. NEVER use visual references like "as you can see", "look at", "watch how", etc.
2. Describe actions, positions, and movements using spatial and physical terms
3. Explain sports terminology in simple, clear language
4. Provide context about scoring, rules, and what makes performances good or bad
5. Use descriptive language that paints an audio picture
6. Be concise but informative - users may be following live action
7. When describing athletes, focus on their movements, technique, and performance
8. For scores and statistics, explain what the numbers mean
9. Be encouraging and positive while remaining accurate

You have access to the recent transcript of what the commentators have said. Use this context to answer questions accurately and provide relevant information about what's happening in the event.

Remember: Your responses will be read aloud, so keep them natural and conversational."""


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
        transcript_context: List[TranscriptEntry],
        sport_type: str = "Winter Olympics event"
    ) -> str:
        """
        Generate an accessibility-friendly answer to a user's question.
        
        Args:
            question: The user's question
            transcript_context: Recent transcript entries for context
            sport_type: The type of sport being watched
            
        Returns:
            The generated answer text
        """
        context_text = self.format_transcript_context(transcript_context)
        
        prompt = f"""{SYSTEM_PROMPT}

CURRENT CONTEXT:
Sport: {sport_type}
Recent Commentary Transcript:
{context_text}

USER QUESTION: {question}

Please provide a helpful, accessible answer. Remember to avoid visual references and explain things clearly for someone who may not be able to see the video or who is new to this sport."""

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
