from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from src.integrations.intervals_icu.client import IntervalsICUClient, IntervalsICUError
from src.services.ai_engine import AIEngine
from src.services.fitness_tracker import FitnessTracker

router = APIRouter(prefix="/api/fitness", tags=["fitness"])
tracker = FitnessTracker()


@router.get("/status")
async def fitness_status() -> dict[str, Any]:
    """Current fitness status (CTL/ATL/TSB, form assessment)."""
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        async with IntervalsICUClient() as client:
            wellness = await client.get_wellness_today()
    except IntervalsICUError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from None

    ctl = wellness.get("ctl", 0) or 0
    atl = wellness.get("atl", 0) or 0

    form = tracker.calculate_form(ctl, atl)
    readiness = tracker.assess_readiness(wellness, form)

    return {
        "date": today,
        "form": form,
        "readiness": readiness,
    }


@router.get("/readiness")
async def training_readiness() -> dict[str, Any]:
    """Today's training readiness score with recommendation."""
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        async with IntervalsICUClient() as client:
            wellness = await client.get_wellness_today()
            events = await client.get_events(today, tomorrow)
    except IntervalsICUError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from None

    ctl = wellness.get("ctl", 0) or 0
    atl = wellness.get("atl", 0) or 0

    form = tracker.calculate_form(ctl, atl)
    readiness = tracker.assess_readiness(wellness, form)

    # Find today's planned event
    planned_today = None
    for event in events:
        event_date = event.get("start_date_local", "")[:10]
        if event_date == today:
            planned_today = event
            break

    recommendation = tracker.training_recommendation(form, readiness, planned_today)

    return {
        "date": today,
        "readiness": readiness,
        "recommendation": recommendation,
        "planned_workout": planned_today,
    }


@router.get("/recommendation")
async def training_recommendation() -> dict[str, str]:
    """AI-powered training recommendation based on all available data."""
    today = datetime.now().strftime("%Y-%m-%d")
    oldest = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    try:
        async with IntervalsICUClient() as client:
            activities = await client.get_activities(oldest, today)
            wellness = await client.get_wellness(oldest, today)
            planned = await client.get_events(today, future)
    except IntervalsICUError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from None

    ai = AIEngine()
    assessment = await ai.assess_fitness(activities, wellness, planned)
    return {"assessment": assessment}
