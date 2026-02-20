from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from src.integrations.intervals_icu.client import IntervalsICUClient, IntervalsICUError
from src.services.activity_analyzer import ActivityAnalyzer
from src.services.ai_engine import AIEngine

router = APIRouter(prefix="/api/activities", tags=["activities"])
analyzer = ActivityAnalyzer()


@router.get("/")
async def list_activities(days: int = 7) -> list[dict[str, Any]]:
    """List recent activities from Intervals.icu."""
    newest = datetime.now().strftime("%Y-%m-%d")
    oldest = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        async with IntervalsICUClient() as client:
            activities = await client.get_activities(oldest, newest)
    except IntervalsICUError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from None

    return [analyzer.analyze(a) for a in activities]


@router.get("/{activity_id}")
async def get_activity(activity_id: str) -> dict[str, Any]:
    """Get detailed activity analysis."""
    try:
        async with IntervalsICUClient() as client:
            activity = await client.get_activity(activity_id)
    except IntervalsICUError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from None

    return analyzer.analyze(activity)


@router.get("/{activity_id}/summary")
async def get_activity_summary(activity_id: str) -> dict[str, str]:
    """Get AI-generated summary of an activity."""
    try:
        async with IntervalsICUClient() as client:
            activity = await client.get_activity(activity_id)
    except IntervalsICUError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from None

    ai = AIEngine()
    summary = await ai.summarize_activity(activity)
    return {"activity_id": activity_id, "summary": summary}
