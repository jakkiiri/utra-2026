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
    Set category="people" when searching for athletes specifically.

    Args:
        query: Search query (e.g., "Khabib Nurmagomedov UFC stats and profile")
        category: Optional category filter:
            - "people": Find people by role/expertise - USE THIS for athlete searches
            - "news": News articles
            - "research paper": Academic papers
            - None: General search (recommended for stats/records)

    Returns:
        JSON string with search results including title, URL, highlights, and score.
        Results are automatically pushed as cards to the user interface.
    """
    if not EXA_API_KEY:
        return json.dumps({"error": "Exa search is not configured"})

    try:
        exa = Exa(api_key=EXA_API_KEY)

        # Make query more specific for athlete searches to avoid common name conflicts
        enhanced_query = query
        if category == "people" and not any(term in query.lower() for term in ["ufc", "mma", "fighter", "athlete", "boxer", "sport"]):
            # Add context to disambiguate common names
            enhanced_query = f"{query} professional athlete fighter"
            print(f"  🔍 Enhanced query: {enhanced_query}")

        # Search with highlights
        results = exa.search_and_contents(
            query=enhanced_query,
            type="auto",  # Balanced relevance and speed
            num_results=8,  # Get more to filter out irrelevant ones
            category=category,
            highlights={
                "num_sentences": 6,
                "highlights_per_url": 6
            }
        )

        # Format and filter results
        formatted = []

        # Spam/irrelevant indicators
        spam_indicators = [
            "cryptocurrency", "crypto mining", "scam", "iva",
            "maintenance ltd", "property maintenance", "linkedin.com/posts",
            "mcgregor projects", "repair and maintenance"
        ]

        # Sports/athlete indicators (for relevance)
        sports_indicators = [
            "ufc", "mma", "fighter", "boxing", "champion", "athlete",
            "martial arts", "combat sports", "knockout", "fight",
            "wrestling", "championship", "octagon", "professional record"
        ]

        for r in results.results:
            title_lower = r.title.lower()
            url_lower = r.url.lower()

            # Skip if spam indicators found
            if any(indicator in title_lower or indicator in url_lower for indicator in spam_indicators):
                print(f"  ⚠️ Filtered out spam result: {r.title[:50]}")
                continue

            # For athlete searches, require sports indicators
            if category == "people":
                highlights_text = " ".join(r.highlights if hasattr(r, 'highlights') else []).lower()
                combined_text = f"{title_lower} {highlights_text}"

                # Must have at least one sports indicator
                if not any(indicator in combined_text for indicator in sports_indicators):
                    print(f"  ⚠️ Filtered out non-athlete result: {r.title[:50]}")
                    continue

            item = {
                "title": r.title,
                "url": r.url,
                "highlights": r.highlights if hasattr(r, 'highlights') else [],
                "score": r.score if hasattr(r, 'score') else 1.0
            }
            formatted.append(item)

        # Limit to top 5 after filtering
        formatted = formatted[:5]

        print(f"  ✅ Filtered results: {len(formatted)} relevant out of {len(results.results)} total")

        # Store for card generation
        _store_exa_results_for_cards(formatted)

        return json.dumps(formatted, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Exa search failed: {str(e)}"})


@tool
async def push_info_card(title: str, content: str, card_type: str = "analysis", source_url: str = "", image_url: str = "") -> str:
    """
    Push an information card to the user interface in real-time.
    Use this to share player profiles, stats, or interesting facts with the user as you discover them.

    Args:
        title: Card title (e.g., "Khabib Nurmagomedov", "UFC Record")
        content: Main content/description for the card
        card_type: Type of card - "player_profile" for athletes, "historical" for facts, "analysis" for insights
        source_url: Optional URL to source (e.g., Wikipedia page)
        image_url: Optional image URL (for player profiles)

    Returns:
        Confirmation that card was pushed

    Example:
        push_info_card(
            title="Khabib Nurmagomedov",
            content="Undefeated UFC lightweight champion with 29-0 record",
            card_type="player_profile",
            source_url="https://en.wikipedia.org/wiki/Khabib_Nurmagomedov",
            image_url="https://example.com/khabib.jpg"
        )
    """
    try:
        # Import here to avoid circular dependency
        from main import manager, WebSocketMessage, WebSocketEventType
        from models import CommentaryItemPush
        import asyncio

        # Create card
        card = CommentaryItemPush(
            type=card_type,
            title=title,
            content=content,
            highlight={
                "value": source_url,
                "label": "Source" if source_url else "",
                "image": image_url,
                "stats": []  # Can be populated by splitting content if needed
            } if source_url or image_url else None
        )

        # Push via WebSocket
        await manager.broadcast(
            WebSocketMessage(
                type=WebSocketEventType.PUSH_COMMENTARY,
                data=card.model_dump()
            )
        )

        return f"✅ Card pushed: {title}"
    except Exception as e:
        return f"❌ Failed to push card: {str(e)}"


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
        return f"Screenshot analysis failed: {str(e)}"


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
                    return f"Screenshot analysis failed: {str(e)}"

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
        # Clear previous Exa results
        clear_exa_results()

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

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are WinterStream AI, an assistant for sports events and live streams.

CRITICAL: You MUST use tools for every question. DO NOT answer from memory alone!

Available Tools (USE THESE):
- search_exa: Search the web for player stats, records, event info, news
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

Tool Usage Priority:
1. For athlete/player questions:
   a. Use search_exa(query="[name] [sport] stats", category="people")
   b. IMMEDIATELY use push_info_card() for each athlete found
   c. Then answer the question

2. For "what's happening" questions:
   a. ALWAYS use get_current_transcript first (tells you what's happening)
   b. Use get_current_video_metadata for event context
   c. Use analyze_current_frame ONLY if screenshot available
   d. Combine info from transcript + metadata to answer

3. For general questions:
   a. Use get_current_video_metadata to understand the event
   b. Use get_current_transcript for recent commentary
   c. Use search_exa if you need additional facts

Examples:
Q: "Who's playing?"
✅ CORRECT:
  1. Use get_current_video_metadata
  2. Use search_exa for Athlete 1
  3. Use push_info_card(title="Athlete 1", content="...", card_type="player_profile")
  4. Use search_exa for Athlete 2
  5. Use push_info_card(title="Athlete 2", content="...", card_type="player_profile")
  6. Answer: "Athlete 1 and Athlete 2 are competing. Check the cards for their profiles!"
❌ WRONG: Search but don't push cards, or say "I'm going to pull up information"

Q: "Tell me about Khabib"
✅ CORRECT:
  1. Use search_exa(query="Khabib Nurmagomedov UFC stats", category="people")
  2. Use push_info_card(title="Khabib Nurmagomedov", content="29-0 record...", card_type="player_profile")
  3. Answer with key facts
❌ WRONG: Answer from memory without search or don't push card

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
- Event: {video_title}
- Current time: {current_time} seconds
- Screenshot available: {has_screenshot}

Tool Strategy:
- If screenshot available → Use analyze_current_frame for visual context
- If screenshot NOT available → Use get_current_transcript (tells you what's happening!)
- NEVER say "I can't answer because screenshot unavailable" - use transcript instead!

User question: {question}"""),
            ("human", "{question}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        agent = create_tool_calling_agent(self.llm, context_tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=context_tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True
        )

        # Prepare input for agent
        agent_input = {
            "question": question,
            "video_title": video_title,
            "current_time": playback_time,
            "has_screenshot": "Yes - use analyze_current_frame to see what's happening NOW" if screenshot_base64 else "No"
        }

        try:
            # Check if this is an athlete/player question that requires search
            athlete_keywords = ["who", "who's", "player", "athlete", "fighter", "playing", "competing"]
            needs_search = any(keyword in question.lower() for keyword in athlete_keywords)

            # Run agent with streaming callbacks
            print(f"🤖 Running agent for question: {question[:50]}...")
            print(f"   Athlete question detected: {needs_search}")
            print(f"   Screenshot available: {'Yes' if screenshot_base64 else 'No'}")

            # Import WebSocket manager for streaming
            from main import manager, WebSocketMessage, WebSocketEventType

            # Stream status update
            await manager.broadcast(WebSocketMessage(
                type=WebSocketEventType.PROCESSING_START,
                data={"status": "Agent is thinking and gathering information..."}
            ))

            # Use async invoke instead of sync to support async tools
            result = await agent_executor.ainvoke(agent_input)

            answer = result.get("output", "I couldn't generate an answer.")
            print(f"✅ Agent response: {answer[:100]}...")

            # Extract tools used from intermediate steps
            tools_used = []
            if "intermediate_steps" in result:
                print(f"📊 Intermediate steps: {len(result['intermediate_steps'])}")
                for step in result["intermediate_steps"]:
                    if len(step) > 0:
                        tool_name = step[0].tool if hasattr(step[0], 'tool') else "unknown"
                        tools_used.append(tool_name)
                        print(f"  🔧 Tool used: {tool_name}")

            # Get Exa results if search was used
            exa_results = get_latest_exa_results()
            print(f"🔍 Exa results found: {len(exa_results)}")

            # Detect bad responses that promise action without taking it
            bad_phrases = [
                "i'm going to pull up",
                "i'll pull up",
                "let me pull up",
                "i'm pulling up",
                "i'll try to get",
                "let me get",
                "i'll keep trying"
            ]
            answer_lower = answer.lower()
            if any(phrase in answer_lower for phrase in bad_phrases):
                print("⚠️ WARNING: Agent promised action without taking it!")

                # If this was an athlete question and no search was used, force a search
                if needs_search and "search_exa" not in tools_used:
                    print("🔄 Forcing Exa search for athlete question...")

                    # Extract sport/event type from title for better context
                    import re
                    sport_keywords = {
                        "ufc": "UFC MMA",
                        "mma": "MMA",
                        "boxing": "boxing",
                        "nfl": "NFL football",
                        "nba": "NBA basketball",
                        "olympics": "Olympics",
                        "soccer": "soccer",
                        "football": "football"
                    }

                    sport_context = ""
                    for keyword, context in sport_keywords.items():
                        if keyword in video_title.lower():
                            sport_context = context
                            break

                    # Create specific search query with sport context
                    if sport_context:
                        search_query = f"{video_title} {sport_context} professional athletes fighter stats"
                    else:
                        search_query = f"{video_title} professional athletes stats"

                    print(f"  📝 Search query: {search_query}")

                    # Do the search directly
                    search_result = search_exa.invoke({"query": search_query, "category": "people"})
                    exa_results = get_latest_exa_results()
                    print(f"✅ Forced search completed: {len(exa_results)} results")

                    # Replace the bad answer with actual information
                    if exa_results:
                        answer = f"Based on the event, I found profiles for the athletes. Check the cards on the right for their stats and backgrounds!"
                    else:
                        answer = "I'm having trouble finding specific athlete information. Could you ask about a specific person by name?"
                    tools_used.append("search_exa")

            # Extract sources from Exa results
            sources = [r["url"] for r in exa_results if "url" in r]

            return {
                "answer": answer,
                "sources": sources,
                "tools_used": list(set(tools_used)),  # Unique tool names
                "exa_results": exa_results
            }

        except Exception as e:
            print(f"❌ Agent error: {e}")
            import traceback
            print(traceback.format_exc())

            # Provide a helpful fallback response
            return {
                "answer": f"I'm having a technical issue right now. Here's what I know about the event based on the title: {video_title}. Please try asking again in a moment.",
                "sources": [],
                "tools_used": [],
                "exa_results": []
            }

    async def research_video_context(
        self,
        video_title: str,
        screenshot_base64: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Proactive research on video load to gather context about players and event.

        Args:
            video_title: YouTube video title
            screenshot_base64: Optional screenshot from video start

        Returns:
            Dictionary with:
            - players: List[dict] - Player information
            - event_info: dict - Event/competition information
            - sport: str - Sport/event type identified
        """
        try:
            # Step 1: Analyze title to extract sport, athletes, competition
            analysis_prompt = f"""
            Analyze this video title: "{video_title}"

            Extract and return as JSON:
            {{
                "sport": "sport or event type (e.g., 'snowboard halfpipe', 'figure skating')",
                "athletes": ["athlete name 1", "athlete name 2"],
                "competition": "competition level (e.g., 'Olympics', 'World Cup', 'Championship')"
            }}

            If no athletes are mentioned, return empty array for athletes.
            """

            analysis_result = await asyncio.to_thread(
                self.llm.invoke,
                analysis_prompt
            )

            # Parse JSON from LLM response
            import re
            json_match = re.search(r'\{.*\}', analysis_result.content, re.DOTALL)
            if json_match:
                extracted_info = json.loads(json_match.group())
            else:
                extracted_info = {"sport": "unknown", "athletes": [], "competition": "unknown"}

            # Step 2: Search for each athlete
            player_data = []
            for athlete in extracted_info.get("athletes", [])[:3]:  # Limit to 3 athletes
                query = f"{athlete} {extracted_info['sport']} stats career highlights"

                # Use Exa search
                exa = Exa(api_key=EXA_API_KEY)
                results = exa.search(
                    query=query,
                    type="auto",
                    num_results=2,
                    category="people",
                    contents={"highlights": {"num_sentences": 4, "highlights_per_url": 4}}
                )

                if results.results:
                    player_data.append({
                        "name": athlete,
                        "info": {
                            "title": results.results[0].title,
                            "url": results.results[0].url,
                            "highlights": results.results[0].highlights if hasattr(results.results[0], 'highlights') else []
                        }
                    })

            # Step 3: Search for event info
            event_query = f"{extracted_info['sport']} {extracted_info['competition']} records rules history"
            exa = Exa(api_key=EXA_API_KEY)
            event_results = exa.search(
                query=event_query,
                type="auto",
                num_results=2,
                contents={"highlights": {"num_sentences": 6, "highlights_per_url": 6}}
            )

            event_info = None
            if event_results.results:
                event_info = {
                    "title": event_results.results[0].title,
                    "url": event_results.results[0].url,
                    "highlights": event_results.results[0].highlights if hasattr(event_results.results[0], 'highlights') else []
                }

            return {
                "players": player_data,
                "event_info": event_info,
                "sport": extracted_info.get("sport", "unknown")
            }

        except Exception as e:
            print(f"Research error: {e}")
            return {
                "players": [],
                "event_info": None,
                "sport": "unknown"
            }


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
        import time

        last_check_time = 0
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
