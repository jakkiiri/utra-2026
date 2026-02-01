"""
Service for AI to proactively push commentary based on video analysis.
"""
import asyncio
from typing import Optional
import httpx
from models import CommentaryItemPush


class CommentaryPusher:
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url

    async def push_insight(
        self,
        content: str,
        item_type: str = 'analysis',
        title: Optional[str] = None,
        highlight: Optional[dict] = None
    ):
        """Push an AI-generated insight to all clients."""
        item = CommentaryItemPush(
            type=item_type,
            content=content,
            title=title,
            highlight=highlight
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/commentary/push",
                json=item.model_dump()
            )
            return response.json()

    async def push_historical_comparison(
        self,
        content: str,
        title: str,
        current: float,
        record: float,
        note: str
    ):
        """Push a historical comparison card."""
        item = CommentaryItemPush(
            type='historical',
            content=content,
            title=title,
            comparison={
                'current': current,
                'record': record,
                'note': note
            }
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/commentary/push",
                json=item.model_dump()
            )
            return response.json()

    async def push_live_update(
        self,
        content: str,
        highlight_value: Optional[str] = None
    ):
        """Push a live event status update."""
        item = CommentaryItemPush(
            type='market_shift',
            content=content,
            highlight={'value': highlight_value} if highlight_value else None
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/commentary/push",
                json=item.model_dump()
            )
            return response.json()

    async def push_narration(
        self,
        content: str,
        title: Optional[str] = None
    ):
        """Push a narration commentary item."""
        item = CommentaryItemPush(
            type='narration',
            content=content,
            title=title
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/commentary/push",
                json=item.model_dump()
            )
            return response.json()

    async def push_event_update(
        self,
        win_probability: Optional[float] = None,
        probability_change: Optional[float] = None,
        technical_score: Optional[float] = None,
        risk_warning: Optional[dict] = None
    ):
        """
        Push event sidebar updates.

        Args:
            win_probability: Win probability percentage (0-100)
            probability_change: Change in probability (can be negative)
            technical_score: Technical score (0-100)
            risk_warning: Dict with title, description, and probability
        """
        update = {}
        if win_probability is not None:
            update['winProbability'] = win_probability
        if probability_change is not None:
            update['probabilityChange'] = probability_change
        if technical_score is not None:
            update['technicalScore'] = technical_score
        if risk_warning is not None:
            update['riskWarning'] = risk_warning

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/event/update",
                json=update
            )
            return response.json()


# Singleton instance
commentary_pusher = CommentaryPusher()
