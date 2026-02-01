"""
LangChain Agent Service - Agentic AI with tool access for sports narration.

This service provides an intelligent agent that can:
- Search the web via Exa for player stats, event info, and records
- Analyze screenshots for visual context
- Access video transcript and metadata
- Maintain accessibility-first, concise responses
"""

import json
import base64
from typing import Optional, List, Dict, Any
import asyncio

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from exa_py import Exa
from google import genai

from config import GEMINI_API_KEY, EXA_API_KEY


# Global cache for Exa results (for card generation)
_exa_result_cache: Dict[str, List[Dict]] = {}

# Global cache for video-specific context
_video_context_cache: Dict[str, Dict] = {}


# =============================================================================
# Tool Definitions
# =============================================================================

@tool
def search_exa(query: str, category: Optional[str] = None) -> str:
    """
    Search the web for current information about sports events, players, and statistics.

    Use this tool to find:
    - Player stats, career highlights, records, photos
    - Current event information, news
    - Historical comparisons and data
    - Rules and technical details
    - Athlete backgrounds, achievements, rankings

    IMPORTANT: When users ask "who's playing" or "who is [athlete]", ALWAYS use this tool!
    ALWAYS set category="people" when searching for athletes/players.

    After using this tool, you MUST:
    1. Analyze and summarize the results
    2. Use push_info_card() to push processed information (not raw search results)
    3. Only push the most relevant, insightful information

    Tips for better athlete searches:
    - Include sport name in query (e.g., "M. Dukurs skeleton athlete")
    - Include nationality if known (e.g., "M. Dukurs Latvia skeleton")
    - Use full names when possible
    - Results automatically filter out LinkedIn and business profiles

    Args:
        query: Search query (e.g., "Khabib Nurmagomedov UFC stats and profile", "M. Dukurs skeleton Latvia")
        category: Optional category filter:
            - "people": Find people by role/expertise - REQUIRED for athlete searches
            - "news": News articles
            - "research paper": Academic papers
            - None: General search (use for event info, rules, records)

    Returns:
        Concise summary of key findings from top results.
        You must then decide what information is worth pushing as cards.
    """
    if not EXA_API_KEY:
        return json.dumps({"error": "Exa search is not configured"})

    try:
        exa = Exa(api_key=EXA_API_KEY)

        # Make query more specific for athlete searches
        enhanced_query = query
        if category == "people":
            # For athlete searches, add sports context if not already present
            if not any(term in query.lower() for term in ["ufc", "mma", "fighter", "athlete", "boxer", "sport", "olympic", "skeleton", "bobsled"]):
                enhanced_query = f"{query} athlete sports"
            print(f"  🔍 Enhanced query: {enhanced_query}")

        # Search with highlights - reduced number for more focused results
        results = exa.search_and_contents(
            query=enhanced_query,
            type="auto",
            num_results=5,  # Reduced from 8 for more focused results
            category=category,
            highlights={
                "num_sentences": 3,  # Reduced from 6 for conciseness
                "highlights_per_url": 3  # Reduced from 6 for conciseness
            }
        )

        # Spam/irrelevant indicators - be specific to avoid filtering athletes
        spam_indicators = [
            "linkedin.com/in/", "linkedin.com/posts", "indeed.com", "glassdoor",
            "cryptocurrency", "crypto mining", "scam",
            "maintenance ltd", "property maintenance",
            "mcgregor projects", "repair and maintenance",
            "job posting", "hiring", "careers", "resume"
        ]

        # Business-only indicators (not sports organizations)
        business_only_indicators = [
            "consulting", "investment", "venture capital",
            "real estate", "insurance", "financial services"
        ]

        # Sports/athlete indicators (expanded for winter sports and general athletics)
        sports_indicators = [
            # Combat sports
            "ufc", "mma", "fighter", "boxing", "martial arts", "knockout",
            # General sports
            "athlete", "champion", "championship", "professional record",
            "olympics", "olympic", "world cup", "medal", "gold medal",
            "competition", "tournament", "sports", "team", "national team",
            # Winter sports
            "skeleton", "bobsled", "luge", "skiing", "snowboard", "ice hockey",
            "figure skating", "speed skating", "curling", "biathlon",
            # Stats and records
            "record holder", "world record", "personal best", "pb",
            "ranked", "ranking", "profile", "biography", "career stats"
        ]

        # Process and extract key insights
        insights = []

        for r in results.results:
            title_lower = r.title.lower()
            url_lower = r.url.lower()

            print(f"  📄 Checking: {r.title[:60]}")
            print(f"      URL: {r.url[:80]}")

            # Get highlights for better content analysis
            highlights_text = ""
            if hasattr(r, 'highlights') and r.highlights:
                highlights_text = " ".join(r.highlights).lower()
                print(f"      Highlights: {highlights_text[:100]}")

            combined_text = f"{title_lower} {highlights_text} {url_lower}"

            # Check for sports content in all results
            sports_matches = [ind for ind in sports_indicators if ind in combined_text]
            has_sports_content = len(sports_matches) > 0

            # For athlete searches, REQUIRE sports content
            if category == "people":
                if not has_sports_content:
                    print(f"  ⚠️ Filtered non-sports (no match)")
                    continue

                print(f"  ✅ Sports content found ({', '.join(sports_matches[:3])})")

            # For LinkedIn profiles, accept ONLY if it's an athlete with sports content
            is_linkedin = "linkedin.com/in/" in url_lower or "linkedin.com/posts" in url_lower
            if is_linkedin:
                if category == "people" and has_sports_content:
                    print(f"  ✅ LinkedIn athlete profile - ACCEPTED")
                else:
                    print(f"  ⚠️ Filtered LinkedIn (not athlete)")
                    continue

            # Skip other obvious spam (not LinkedIn)
            spam_match = None
            for indicator in spam_indicators:
                if indicator not in ["linkedin.com/in/", "linkedin.com/posts"]:  # Skip LinkedIn indicators
                    if indicator in title_lower or indicator in url_lower:
                        spam_match = indicator
                        break

            if spam_match:
                print(f"  ⚠️ Filtered spam (matched: '{spam_match}')")
                continue

            # Skip business-only profiles
            business_match = None
            for indicator in business_only_indicators:
                if indicator in title_lower:
                    business_match = indicator
                    break

            if business_match:
                print(f"  ⚠️ Filtered business (matched: '{business_match}')")
                continue

            # Extract structured insight
            insight = {
                "source_title": r.title,
                "source_url": r.url,
                "key_points": r.highlights if hasattr(r, 'highlights') else [],
                "image_url": r.image if hasattr(r, 'image') else None
            }
            insights.append(insight)

        # Limit to top 3 most relevant
        insights = insights[:3]

        print(f"  ✅ Extracted {len(insights)} insights from search")

        # Store raw insights for agent to process
        _store_exa_results_for_cards(insights)

        # Return concise summary for agent to analyze
        if not insights:
            return "No relevant results found. Try refining the search query or checking the spelling."

        summary = f"Found {len(insights)} relevant sources:\n\n"
        for i, insight in enumerate(insights, 1):
            summary += f"{i}. {insight['source_title']}\n"
            if insight['key_points']:
                summary += f"   Key info: {insight['key_points'][0]}\n"
            summary += f"   Source: {insight['source_url']}\n\n"

        summary += "IMPORTANT: Analyze these results and use push_info_card() to share the most valuable insights with the user. Do not dump raw results."

        return summary

    except Exception as e:
        # Log error for debugging but provide clean message to agent
        print(f"❌ Exa search error: {str(e)}")
        return "Search service temporarily unavailable. Try using video metadata and transcript to answer the question."


# Track pushed cards to detect duplicates within a request
_pushed_cards_tracker: List[str] = []

def _reset_card_tracker():
    """Reset the card tracker for a new request"""
    global _pushed_cards_tracker
    _pushed_cards_tracker = []

@tool
async def push_info_card(
    title: str,
    content: str,
    card_type: str = "analysis",
    source_url: str = "",
    image_url: str = "",
    stats: Optional[List[str]] = None
) -> str:
    """
    Push an information card to the user interface in real-time.
    Use this to share player profiles, stats, or interesting facts AFTER analyzing search results.

    CRITICAL: Only push processed, insightful information. Do NOT push raw search results.
    Always analyze and summarize before pushing.
    DO NOT push the same card twice - check if you already pushed this information!

    Args:
        title: Card title (e.g., "Khabib Nurmagomedov", "UFC Record")
        content: Concise 1-2 sentence summary (your analysis, not raw text)
        card_type: Type of card:
            - "player_profile": For athlete profiles with stats
            - "historical": For historical facts or context
            - "analysis": For insights and analysis
        source_url: URL to source for verification
        image_url: Image URL (for player profiles)
        stats: List of 3-5 key statistics as bullet points (e.g., ["Record: 29-0", "Titles: 3"])

    Returns:
        Confirmation that card was pushed

    Example:
        # Good - processed and summarized:
        push_info_card(
            title="Khabib Nurmagomedov",
            content="Retired undefeated as UFC lightweight champion, known for dominant grappling.",
            card_type="player_profile",
            source_url="https://ufc.com/athlete/khabib",
            stats=["Record: 29-0", "UFC Title Defenses: 3", "Submission wins: 8"]
        )

        # Bad - raw dump:
        push_info_card(title="Search Result", content="<raw highlight text>")
    """
    try:
        global _pushed_cards_tracker

        # Check for duplicate
        card_key = f"{title}:{card_type}"
        if card_key in _pushed_cards_tracker:
            print(f"⚠️ DUPLICATE DETECTED: Card '{title}' already pushed, skipping")
            return f"⚠️ Card '{title}' was already pushed. Skipped duplicate."

        print(f"📤 push_info_card called: {title}")
        _pushed_cards_tracker.append(card_key)

        # Import here to avoid circular dependency
        from main import manager, WebSocketMessage, WebSocketEventType
        from models import CommentaryItemPush

        # Create card with structured stats
        card = CommentaryItemPush(
            type=card_type,
            title=title,
            content=content,
            highlight={
                "value": source_url,
                "label": "Source" if source_url else "",
                "image": image_url,
                "stats": stats or []
            } if (source_url or image_url or stats) else None
        )

        print(f"  📋 Card created: type={card_type}, has_highlight={card.highlight is not None}")

        # Push via WebSocket
        await manager.broadcast(
            WebSocketMessage(
                type=WebSocketEventType.PUSH_COMMENTARY,
                data=card.model_dump()
            )
        )

        print(f"  ✅ Card broadcast complete: {title}")
        return f"✅ Card pushed: {title}"
    except Exception as e:
        # Log error but don't expose details to agent/user
        print(f"❌ Failed to push card: {str(e)}")
        return "Card push failed. Continuing with answer..."


@tool
async def analyze_screenshot(screenshot_base64: str, focus: str = "general") -> str:
    """
    Analyze a screenshot from the video for visual context using Gemini Vision.

    Use this tool when:
    - User asks about what's happening in the video
    - You need to identify athletes, actions, or environment
    - Visual context would help answer the question

    Args:
        screenshot_base64: Base64 encoded JPEG screenshot from the video
        focus: What to focus on in the analysis (e.g., "identify athletes", "describe action", "environment")

    Returns:
        Description of what's visible in the screenshot
    """
    if not screenshot_base64:
        return "No screenshot provided"

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        prompt = f"Describe what's happening in this sports video frame. Focus on: {focus}. Be concise and descriptive."

        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": screenshot_base64
                            }
                        }
                    ]
                }
            ]
        )

        return response.text

    except Exception as e:
        print(f"❌ Screenshot analysis error: {str(e)}")
        return "Screenshot analysis unavailable. Use transcript and metadata instead."


# =============================================================================
# Helper Functions
# =============================================================================

def _store_exa_results_for_cards(results: List[Dict]):
    """Store Exa search results for later card generation"""
    global _exa_result_cache
    # Store latest results (will be retrieved by main.py for card generation)
    _exa_result_cache["latest"] = results


def get_latest_exa_results() -> List[Dict]:
    """Retrieve latest Exa results for card generation"""
    global _exa_result_cache
    return _exa_result_cache.get("latest", [])


def clear_exa_results():
    """Clear Exa result cache"""
    global _exa_result_cache
    _exa_result_cache.clear()


def _store_video_context(video_id: str, context: Dict):
    """Store video-specific context from proactive search"""
    global _video_context_cache
    _video_context_cache[video_id] = context
    print(f"  💾 Cached context for video {video_id}")


def _get_video_context(video_id: str) -> Optional[Dict]:
    """Retrieve cached video context"""
    global _video_context_cache
    return _video_context_cache.get(video_id)


# =============================================================================
# Agent Service Class
# =============================================================================

class AgentService:
    """
    LangChain-based agentic service for answering sports-related questions.

    The agent has access to:
    - Exa web search for current stats and information
    - Screenshot analysis via Gemini Vision
    - Video transcript and metadata
    - Gemini 2.0 Flash as the reasoning LLM
    """

    def __init__(self):
        self.llm = self._setup_llm()
        self.tools = self._setup_tools()
        self.agent_executor = self._create_agent()

    def _setup_llm(self) -> ChatGoogleGenerativeAI:
        """Initialize the Gemini LLM via LangChain"""
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0.7,
            convert_system_message_to_human=True  # Gemini compatibility
        )

    def _setup_tools(self) -> List:
        """Setup all available tools for the agent"""
        return [
            search_exa,
            analyze_screenshot,
            push_info_card
        ]

    def _setup_context_tools(self, video_id: str, playback_time: float, screenshot_base64: Optional[str] = None) -> List:
        """Setup context-aware tools for the current question"""
        from functools import partial

        # Create tools bound to current video context
        @tool
        def get_current_transcript() -> str:
            """
            Get recent video transcript/commentary context from the current playback position.
            This tool automatically uses the current video and playback time.

            Use this to:
            - Access what was said in the video recently
            - Get context about current events in the video
            - Find specific quotes or commentary
            """
            try:
                from services.youtube_service import YouTubeService
                print(f"  📝 Getting transcript for {video_id} at {playback_time}s")
                context = YouTubeService.get_context_text(video_id, playback_time)
                if not context or context == "":
                    print("  ⚠️ No transcript available")
                    return "No transcript available for this stream. This is likely a live event without captions. You can still answer based on the video metadata and search for information about the event."
                print(f"  ✅ Transcript retrieved: {len(context)} chars")
                return context
            except Exception as e:
                print(f"  ❌ Transcript error: {e}")
                return f"Transcript temporarily unavailable. Try using video metadata or searching for information about the event instead. Error: {str(e)}"

        @tool
        def get_current_video_metadata() -> str:
            """
            Get current video metadata including title, author, and description.
            This tool automatically uses the current video.

            Use this to:
            - Understand what video/event this is
            - Get context about the competition or athletes
            - Find event details from video information
            """
            try:
                from services.youtube_service import YouTubeService
                print(f"  📺 Getting metadata for {video_id}")
                metadata = YouTubeService.get_stored_metadata(video_id)
                if not metadata:
                    print("  ⚠️ No stored metadata, using fallback")
                    # Fallback to the metadata we already have
                    return json.dumps({
                        "title": video_title,
                        "author": "Unknown",
                        "description": "Metadata temporarily unavailable. You can still search for information about this event."
                    }, indent=2)
                print(f"  ✅ Metadata retrieved: {metadata.get('title', 'Unknown')}")
                return json.dumps({
                    "title": metadata.get("title", "Unknown"),
                    "author": metadata.get("author", "Unknown"),
                    "description": metadata.get("description", "No description available")
                }, indent=2)
            except Exception as e:
                print(f"  ❌ Metadata error: {e}")
                # Return fallback metadata instead of error
                return json.dumps({
                    "title": video_title,
                    "author": "Unknown",
                    "description": f"Using cached title: {video_title}. You can search for more information about this event."
                }, indent=2)

        tools_list = [
            search_exa,
            push_info_card,
            get_current_transcript,
            get_current_video_metadata
        ]

        # Add screenshot analysis tool if screenshot is available
        if screenshot_base64:
            @tool
            async def analyze_current_frame(focus: str = "general") -> str:
                """
                Analyze the current frame/screenshot to see what's happening RIGHT NOW.
                This tool automatically uses the current screenshot.

                Use this to:
                - See what's happening in the event right now
                - Identify athletes, actions, or key moments
                - Understand the current state of play

                Args:
                    focus: What to focus on (e.g., "identify athletes", "describe action", "score")
                """
                try:
                    from google import genai
                    from config import GEMINI_API_KEY

                    client = genai.Client(api_key=GEMINI_API_KEY)
                    prompt = f"Describe what's happening in this sports event frame. Focus on: {focus}. Be concise and descriptive."

                    # Use async properly now that agent supports it
                    response = await client.aio.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[{
                            "role": "user",
                            "parts": [
                                {"text": prompt},
                                {"inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": screenshot_base64
                                }}
                            ]
                        }]
                    )
                    return response.text
                except Exception as e:
                    print(f"❌ Screenshot analysis error: {str(e)}")
                    return "Screenshot analysis unavailable. Use transcript and metadata instead."

            tools_list.append(analyze_current_frame)
        else:
            tools_list.append(analyze_screenshot)  # Add generic version if no screenshot

        return tools_list

    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with tools"""
        from langchain_core.prompts import MessagesPlaceholder

        # System prompt - maintains accessibility-first, concise style
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are WinterStream AI, an assistant for Winter Olympics and sports events.

Your purpose is to help users understand what's happening in sports videos through audio narration.

Available Tools:
- search_exa: Search the web for player stats, records, event info, news
- analyze_screenshot: Analyze video frames for visual context
- get_transcript_context: Access video commentary/transcript
- get_video_metadata: Get video title, description, channel info

Guidelines:
1. Keep answers to 2-3 sentences maximum (will be read aloud)
2. Use casual, friendly tone - be conversational
3. NO visual references (e.g., don't say "as you can see") - accessibility-first
4. Use search_exa proactively for current stats, records, player info
5. Cite sources when using external data (mention where info came from)
6. Be accurate - if unsure, search for information rather than guessing
7. Focus on answering the specific question asked
8. ALWAYS use tools when available - use get_video_metadata and get_transcript_context for video context

Context:
- Video ID: {video_id}
- Video: {video_title}
- Playback time: {current_time} seconds

When using tools, pass the following parameters:
- get_video_metadata: video_id = "{video_id}"
- get_transcript_context: video_id = "{video_id}", playback_time = {current_time}

User question: {question}"""),
            ("human", "{question}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        agent = create_tool_calling_agent(self.llm, self.tools, prompt)

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,  # Log tool usage for debugging
            max_iterations=5,  # Limit reasoning steps
            handle_parsing_errors=True
        )

    async def answer_question(
        self,
        question: str,
        video_id: str,
        playback_time: float,
        screenshot_base64: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer a user question using agentic approach with tool access.

        Args:
            question: User's question
            video_id: YouTube video ID
            playback_time: Current playback position in seconds
            screenshot_base64: Optional base64 encoded screenshot

        Returns:
            Dictionary with:
            - answer: str - The answer text
            - sources: List[str] - URLs of sources used
            - tools_used: List[str] - Names of tools invoked
            - exa_results: List[dict] - Exa search results for card generation
        """
        # Clear previous Exa results and card tracker
        clear_exa_results()
        _reset_card_tracker()

        # Debug screenshot data
        if screenshot_base64:
            print(f"📸 Screenshot received: {len(screenshot_base64)} chars")
            print(f"   First 50 chars: {screenshot_base64[:50]}")
            print(f"   Last 50 chars: {screenshot_base64[-50:]}")

            # Test if it's valid base64
            import base64 as b64
            try:
                decoded = b64.b64decode(screenshot_base64)
                print(f"   ✅ Valid base64, decoded to {len(decoded)} bytes")

                # Save to file for inspection
                debug_path = f"/tmp/screenshot_debug_{int(playback_time)}.jpg"
                with open(debug_path, 'wb') as f:
                    f.write(decoded)
                print(f"   💾 Saved to {debug_path} for inspection")
            except Exception as e:
                print(f"   ❌ Invalid base64: {e}")
        else:
            print("📸 No screenshot provided")

        # Validate inputs
        if not video_id:
            print("❌ Error: No video_id provided")
            return {
                "answer": "I need a video to be loaded first. Please load a video and try again.",
                "sources": [],
                "tools_used": [],
                "exa_results": []
            }

        # Get video metadata for context
        from services.youtube_service import YouTubeService
        metadata = YouTubeService.get_stored_metadata(video_id)

        if not metadata:
            print(f"⚠️ Warning: No metadata found for video_id: {video_id}")
            # Try to fetch metadata if it's missing
            try:
                metadata = await YouTubeService.get_video_metadata(video_id)
                print(f"✅ Fetched metadata: {metadata.get('title', 'Unknown')}")
            except Exception as e:
                print(f"❌ Failed to fetch metadata: {e}")
                return {
                    "answer": "I'm having trouble accessing the video information. Please try reloading the video.",
                    "sources": [],
                    "tools_used": [],
                    "exa_results": []
                }

        video_title = metadata.get("title", "Unknown video")
        print(f"📹 Video context: {video_title} at {playback_time}s")

        # Check if we have cached context from proactive search
        cached_context = _get_video_context(video_id)
        if cached_context:
            print(f"  ✅ Using cached context: {cached_context.get('profiles_cached', 0)} profiles available")
        else:
            print(f"  ℹ️ No cached context available")

        # Create context-aware tools for this specific question
        try:
            context_tools = self._setup_context_tools(video_id, playback_time, screenshot_base64)
            print(f"🔧 Created {len(context_tools)} context-aware tools")
        except Exception as e:
            print(f"❌ Failed to create tools: {e}")
            return {
                "answer": "I encountered an issue setting up my tools. Please try again.",
                "sources": [],
                "tools_used": [],
                "exa_results": []
            }

        # Create a temporary agent executor with context-bound tools
        from langchain_core.prompts import MessagesPlaceholder

        # Build cached info section if available
        cached_section = ""
        if cached_context and cached_context.get('profiles_cached', 0) > 0:
            sport = cached_context.get('sport', 'Unknown')
            count = cached_context.get('profiles_cached', 0)
            cached_section = f"\n\nCACHED CONTEXT AVAILABLE:\n- Sport: {sport}\n- {count} athlete profile(s) already searched and cached\n- Use search_exa to retrieve cached results (faster than fresh search)\n"

        system_prompt = f"""You are WinterStream AI, an assistant for sports events and live streams.

CRITICAL RULES - YOU MUST FOLLOW THESE:
1. ALWAYS use tools - DO NOT answer from memory alone
2. NEVER give up if one tool fails - try alternative approaches
3. ALWAYS extract athlete names from video title/metadata first
4. When searching for athletes, ALWAYS use category="people" (REQUIRED!)
5. If search fails, use transcript and metadata to extract information
{cached_section}
Available Tools (USE THESE):
- search_exa: Search the web for player stats, records, event info, news (may use cached results for speed)
  IMPORTANT: When searching for athletes, you MUST pass category="people"
- push_info_card: Push info cards to user interface AS YOU FIND INFORMATION (use this proactively!)
- analyze_screenshot: Analyze current frame for what's happening visually RIGHT NOW
- get_current_transcript: Access recent commentary/captions (automatically uses current stream and time)
- get_current_video_metadata: Get event title, description, channel info (automatically uses current stream)

FORBIDDEN PHRASES (Never say these):
❌ "I'm going to pull up"
❌ "I'll pull up"
❌ "Let me get"
❌ "I'll try to get"
❌ "I'm pulling up"
If you say these, you FAILED to use tools properly!

Tool Usage Strategy (BE RESILIENT - never give up!):

STEP 1: ALWAYS get video metadata first
- Use get_current_video_metadata to see event title
- Extract athlete names from title (e.g., "Skeleton - Men's Heats" → search for skeleton athletes)
- Extract sport, event type, date

STEP 2: For athlete/player questions - REQUIRED SEQUENCE:
   a. Get video metadata (extract names from title)
   b. Get transcript (may mention athlete names)
   c. For EACH athlete name found:
      - Use search_exa with category="people" (MANDATORY!)
      - Query format: "[Athlete Name] [Sport] [Country if known] athlete profile stats"
      - Example: search_exa(query="M. Dukurs skeleton Latvia athlete profile", category="people")
   d. If search fails:
      - DON'T say "search unavailable"
      - Extract info from transcript about the athlete
      - Use what you know from video title/metadata
      - Still push a card with available info
   e. For each athlete, use push_info_card with summary
   f. Answer with what you found

STEP 3: For "what's happening" questions:
   a. Use get_current_transcript (tells you what's happening NOW)
   b. Use get_current_video_metadata for event context
   c. Use analyze_current_frame if screenshot available
   d. Combine all sources to answer

CRITICAL FALLBACK RULES:
- If search_exa fails → Extract from transcript and metadata instead
- If transcript unavailable → Use metadata and describe the event
- If all fails → Use video title to provide context about the sport and event
- NEVER say "I can't help" - always provide SOMETHING useful

EFFICIENCY:
- Use get_current_video_metadata FIRST (always)
- ONE search can cover multiple athletes
- Don't repeat searches
- Push all cards before answering

CRITICAL: Never push raw search results. Always:
- Extract the most important 3-5 facts
- Summarize in concise, engaging language
- Format stats as clean bullet points (e.g., "Record: 29-0", "Titles: 3")
- Only push if the information adds real value

Examples:
Q: "Who's playing?" (Video title: "Skeleton - Men's Heats 1 & 2 | Sochi 2014")
✅ CORRECT:
  1. Use get_current_video_metadata → See title mentions "Skeleton" and "Men's Heats"
  2. Use get_current_transcript → Extract athlete names mentioned
  3. search_exa(query="M. Dukurs skeleton Latvia athlete profile", category="people")
  4. If search succeeds: push_info_card with athlete profile
  5. If search fails: Use transcript info to create card anyway
  6. Answer: "M. Dukurs from Latvia is competing in skeleton. Check the card for his profile!"
❌ WRONG:
  - search_exa without category="people"
  - Giving up if search fails
  - Not extracting names from video title

Q: "Tell me about Khabib"
✅ CORRECT:
  1. search_exa(query="Khabib Nurmagomedov UFC MMA fighter stats", category="people")
  2. push_info_card(title="Khabib Nurmagomedov", content="Retired undefeated...", card_type="player_profile", stats=[...])
  3. Answer with key facts
❌ WRONG:
  - search_exa without category="people"
  - Answer from memory without search
  - Don't push card

Q: "Give me information cards" or "Show me cards"
✅ CORRECT:
  1. get_current_video_metadata → Extract athlete names from title
  2. get_current_transcript → Look for more athlete mentions
  3. For each athlete: search_exa(query="[name] [sport] athlete", category="people")
  4. For each athlete: push_info_card with profile
  5. Answer: "I've sent profile cards for the athletes!"
❌ WRONG:
  - Not using category="people"
  - Just describing athletes without pushing cards
  - Giving up if search fails

Response Format:
- Start with facts from tools
- Keep to 2-3 sentences
- Results appear as cards automatically
- Never promise future actions

Guidelines:
1. Keep answers to 2-3 sentences maximum (will be read aloud)
2. Use casual, friendly tone - be conversational
3. NO visual references (e.g., don't say "as you can see" or "the video shows") - accessibility-first
4. Focus on what's happening RIGHT NOW in the event, use present tense
5. When screenshot is available, describe the current action/moment
6. CRITICAL: Use search_exa proactively - DON'T say "I'm searching" or "I'll pull up", just DO IT
7. NEVER say you're "pulling up" or "getting" data - actually use tools and return results
8. Cite sources when using external data (mention where info came from)
9. Be accurate - if unsure, search for information rather than guessing
10. If you use search_exa, results will automatically appear as cards for the user

Context:
- Event: {{video_title}}
- Current time: {{current_time}} seconds
- Screenshot available: {{has_screenshot}}

Tool Strategy:
- If screenshot available → Use analyze_current_frame for visual context
- If screenshot NOT available → Use get_current_transcript (tells you what's happening!)
- NEVER say "I can't answer because screenshot unavailable" - use transcript instead!

User question: {{question}}"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        agent = create_tool_calling_agent(self.llm, context_tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=context_tools,
            verbose=False,  # Disable verbose to reduce noise
            max_iterations=10,  # Increased from 5 to allow for multi-step tasks
            handle_parsing_errors=True,
            early_stopping_method="generate"  # Generate final answer even if max iterations reached
        )

        # Prepare input for agent
        agent_input = {
            "question": question,
            "video_title": video_title,
            "current_time": playback_time,
            "has_screenshot": "Yes - use analyze_current_frame to see what's happening NOW" if screenshot_base64 else "No"
        }

        try:
            # Run agent with streaming callbacks
            print(f"🤖 Running agent for question: {question[:50]}...")
            print(f"   Screenshot available: {'Yes' if screenshot_base64 else 'No'}")
            print(f"   Cached context: {'Yes' if cached_context else 'No'}")

            # Import WebSocket manager for streaming
            from main import manager, WebSocketMessage, WebSocketEventType

            # Stream status update
            await manager.broadcast(WebSocketMessage(
                type=WebSocketEventType.PROCESSING_START,
                data={"status": "Processing your question..."}
            ))

            # Use async invoke instead of sync to support async tools
            result = await agent_executor.ainvoke(agent_input)

            answer = result.get("output", "I couldn't generate an answer.")
            print(f"✅ Agent response: {answer[:100]}...")

            # Extract tools used from intermediate steps
            tools_used = []
            cards_pushed = 0
            iterations_used = 0
            if "intermediate_steps" in result:
                iterations_used = len(result['intermediate_steps'])
                print(f"📊 Intermediate steps: {iterations_used} / 10 iterations used")
                for step in result["intermediate_steps"]:
                    if len(step) > 0:
                        tool_name = step[0].tool if hasattr(step[0], 'tool') else "unknown"
                        tools_used.append(tool_name)
                        if tool_name == "push_info_card":
                            cards_pushed += 1
                        print(f"  🔧 Tool used: {tool_name}")

                # Warn if hitting limits
                if iterations_used >= 9:
                    print(f"  ⚠️ WARNING: Agent used {iterations_used}/10 iterations - might need optimization")

            # Get Exa results if search was used
            exa_results = get_latest_exa_results()
            if exa_results:
                print(f"🔍 Exa results: {len(exa_results)} profiles")

            # Log card push status
            unique_cards = len(_pushed_cards_tracker)
            print(f"📊 Summary: {unique_cards} unique cards pushed, {len(tools_used)} tools used")

            # Extract sources from Exa results
            sources = []
            if exa_results:
                for r in exa_results:
                    if "source_url" in r:
                        sources.append(r["source_url"])
                    elif "url" in r:
                        sources.append(r["url"])

            return {
                "answer": answer,
                "sources": sources,
                "tools_used": list(set(tools_used)),  # Unique tool names
                "exa_results": exa_results
            }

        except Exception as e:
            # Log full error for debugging, but provide clean user-facing message
            print(f"❌ Agent error: {e}")
            import traceback
            print(traceback.format_exc())

            # Provide a clean fallback response without error details
            return {
                "answer": "I'm having trouble answering right now. Please try again in a moment.",
                "sources": [],
                "tools_used": [],
                "exa_results": []
            }

    async def proactive_video_research(
        self,
        video_title: str,
        video_id: str
    ):
        """
        Proactive background research when video loads.
        Searches for relevant information and stores as context WITHOUT agent response.

        This does:
        1. Extract athlete/player names from title
        2. Search for their profiles (Exa)
        3. Store results as context for future questions
        4. NO cards pushed, NO agent response - silent background task

        Args:
            video_title: YouTube video title
            video_id: YouTube video ID
        """
        try:
            print(f"🔍 Starting silent proactive research for: {video_title}")

            # Extract potential athlete names and sport context
            title_lower = video_title.lower()

            # Detect sport type from title
            sport_keywords = {
                "ufc": "UFC MMA", "mma": "MMA", "boxing": "boxing",
                "olympics": "Olympics", "winter olympics": "Winter Olympics",
                "figure skating": "figure skating", "snowboarding": "snowboarding",
                "skiing": "skiing", "ice hockey": "ice hockey"
            }

            sport_context = None
            for keyword, context in sport_keywords.items():
                if keyword in title_lower:
                    sport_context = context
                    break

            if not sport_context:
                print("  ⚠️ No sport detected, skipping proactive search")
                return

            # Build search query from title
            search_query = f"{video_title} professional athletes profiles stats"
            print(f"  📝 Search query: {search_query}")

            # Do direct search WITHOUT agent (just store context)
            search_exa.invoke({
                "query": search_query,
                "category": "people"
            })

            # Results are automatically stored in cache by search_exa
            exa_results = get_latest_exa_results()
            print(f"✅ Silent research completed: {len(exa_results)} profiles cached")

            # Store in video-specific context for future use
            _store_video_context(video_id, {
                "sport": sport_context,
                "profiles_cached": len(exa_results),
                "search_query": search_query
            })

        except Exception as e:
            print(f"⚠️ Proactive research failed (non-critical): {e}")


    async def start_live_monitoring(
        self,
        video_id: str,
        check_interval: int = 30
    ):
        """
        Start continuous monitoring of the video stream.
        Generates proactive insights and commentary at key moments.

        Args:
            video_id: YouTube video ID to monitor
            check_interval: Seconds between checks (default 30)
        """
        print(f"🔴 Starting live monitoring for {video_id} (checking every {check_interval}s)")

        from main import manager, WebSocketMessage, WebSocketEventType
        from services.youtube_service import YouTubeService

        check_count = 0

        while True:
            try:
                await asyncio.sleep(check_interval)
                check_count += 1

                # Get current playback position (would need to track this from frontend)
                # For now, we'll use a simple counter
                current_time = check_count * check_interval

                print(f"📊 Live check #{check_count} at ~{current_time}s")

                # Get video metadata
                metadata = YouTubeService.get_stored_metadata(video_id)
                if not metadata:
                    continue

                video_title = metadata.get("title", "Unknown")

                # Get recent transcript
                context_text = YouTubeService.get_context_text(video_id, current_time)

                # Generate proactive insight if there's interesting context
                if context_text and len(context_text) > 50:
                    # Push a proactive commentary card
                    from models import CommentaryItemPush

                    card = CommentaryItemPush(
                        type="analysis",
                        title="Live Update",
                        content=f"Currently at {current_time}s in {video_title}"
                    )

                    await manager.broadcast(WebSocketMessage(
                        type=WebSocketEventType.PUSH_COMMENTARY,
                        data=card.model_dump()
                    ))

                    print(f"  ✅ Pushed live update")

            except asyncio.CancelledError:
                print("🛑 Live monitoring stopped")
                break
            except Exception as e:
                print(f"  ⚠️ Live monitoring error: {e}")
                continue


# =============================================================================
# Global Instance
# =============================================================================

# Create single instance to reuse across requests
agent_service = AgentService()

# Background task for live monitoring (can be started on video load)
_live_monitoring_task = None


async def start_live_agent(video_id: str):
    """Start the live monitoring agent in background"""
    global _live_monitoring_task

    # Stop previous monitoring if any
    if _live_monitoring_task and not _live_monitoring_task.done():
        _live_monitoring_task.cancel()

    # Start new monitoring
    _live_monitoring_task = asyncio.create_task(
        agent_service.start_live_monitoring(video_id)
    )
    return _live_monitoring_task


def stop_live_agent():
    """Stop the live monitoring agent"""
    global _live_monitoring_task
    if _live_monitoring_task:
        _live_monitoring_task.cancel()
        _live_monitoring_task = None
