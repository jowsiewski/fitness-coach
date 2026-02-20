from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from src.integrations.intervals_icu.client import IntervalsICUClient, IntervalsICUError
from src.services.ai_engine import AIEngine
from src.services.nutrition_planner import NutritionPlanner

router = APIRouter(prefix="/api/nutrition", tags=["nutrition"])
planner = NutritionPlanner()


@router.get("/today")
async def nutrition_today() -> dict[str, Any]:
    """Today's nutrition plan based on training load."""
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        async with IntervalsICUClient() as client:
            wellness = await client.get_wellness_today()
            today_events = await client.get_events(today, today)
            tomorrow_events = await client.get_events(tomorrow, tomorrow)
            today_activities = await client.get_activities(today, today)
    except IntervalsICUError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from None

    weight = wellness.get("weight", 75) or 75
    base_needs = planner.calculate_base_needs(weight)

    today_load = 0.0
    today_duration = 0.0
    if today_activities:
        for a in today_activities:
            today_load += a.get("icu_training_load", 0) or 0
            today_duration += (a.get("moving_time", 0) or 0) / 3600
    elif today_events:
        for ev in today_events:
            today_load += ev.get("icu_training_load", 0) or 0
            today_duration += (ev.get("moving_time", 0) or 0) / 3600

    # Tomorrow's planned load
    tomorrow_load = sum((ev.get("icu_training_load", 0) or 0) for ev in tomorrow_events)

    if today_load > 0:
        plan = planner.plan_for_training_day(base_needs, today_load, today_duration)
    else:
        plan = planner.plan_for_rest_day(base_needs)

    # Add AI-generated detailed plan
    ai = AIEngine()
    ai_plan = await ai.plan_nutrition(weight, today_load, tomorrow_load)

    return {
        "date": today,
        "weight_kg": weight,
        "training_load_today": today_load,
        "planned_load_tomorrow": tomorrow_load,
        "calculated_plan": plan,
        "ai_plan": ai_plan,
    }


@router.get("/plan")
async def nutrition_plan(date: str = "") -> dict[str, Any]:
    """Nutrition plan for a specific date."""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    try:
        async with IntervalsICUClient() as client:
            wellness_list = await client.get_wellness(date, date)
            events = await client.get_events(date, date)
            activities = await client.get_activities(date, date)
    except IntervalsICUError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from None

    wellness = wellness_list[0] if wellness_list else {}
    weight = wellness.get("weight", 75) or 75
    base_needs = planner.calculate_base_needs(weight)

    load = 0.0
    duration = 0.0
    if activities:
        for a in activities:
            load += a.get("icu_training_load", 0) or 0
            duration += (a.get("moving_time", 0) or 0) / 3600
    elif events:
        for ev in events:
            load += ev.get("icu_training_load", 0) or 0
            duration += (ev.get("moving_time", 0) or 0) / 3600

    if load > 0:
        plan = planner.plan_for_training_day(base_needs, load, duration)
    else:
        plan = planner.plan_for_rest_day(base_needs)

    return {
        "date": date,
        "weight_kg": weight,
        "training_load": load,
        "plan": plan,
    }
