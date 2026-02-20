from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from src.integrations.intervals_icu.client import IntervalsICUClient, IntervalsICUError
from src.services.ai_engine import AIEngine

router = APIRouter(prefix="/api/wellness", tags=["wellness"])


@router.get("/")
async def list_wellness(days: int = 30) -> list[dict[str, Any]]:
    """Recent wellness data from Intervals.icu."""
    newest = datetime.now().strftime("%Y-%m-%d")
    oldest = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        async with IntervalsICUClient() as client:
            data = await client.get_wellness(oldest, newest)
    except IntervalsICUError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from None

    return data


@router.get("/trends")
async def wellness_trends(days: int = 30) -> dict[str, Any]:
    """AI analysis of wellness data trends."""
    newest = datetime.now().strftime("%Y-%m-%d")
    oldest = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        async with IntervalsICUClient() as client:
            data = await client.get_wellness(oldest, newest)
    except IntervalsICUError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from None

    if not data:
        return {"analysis": "Brak danych wellness do analizy."}

    ai = AIEngine()
    analysis = await ai.analyze_wellness_trends(data)
    return {"period_days": days, "analysis": analysis}
