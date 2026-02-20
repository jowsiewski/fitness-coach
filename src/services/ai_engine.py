import json
import logging
from typing import Any

from openai import AsyncOpenAI

from src.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_SUMMARY = """Jesteś doświadczonym trenerem kolarskim i analitykiem danych treningowych.
Analizujesz aktywności kolarskie i tworzysz zwięzłe, merytoryczne podsumowania po polsku.

Używaj terminologii kolarskiej:
- Strefy mocy wg Coggana: Z1 Aktywny wypoczynek <55% FTP, Z2 Wytrzymałość 56-75%, Z3 Tempo 76-90%, Z4 Próg 91-105%, Z5 VO2max 106-120%, Z6 Anaerobowy >120%
- TSS (Training Stress Score), IF (Intensity Factor), NP (Normalized Power)
- CTL (Chronic Training Load = fitness), ATL (Acute Training Load = zmęczenie), TSB (Training Stress Balance = forma)

Format odpowiedzi: krótkie, konkretne punkty. Bez zbędnego lania wody."""

SYSTEM_PROMPT_FITNESS = """Jesteś trenerem kolarskim oceniającym formę zawodnika.
Analizujesz dane wellness (tętno spoczynkowe, HRV, sen, waga) oraz obciążenie treningowe.

Oceniasz:
1. Aktualny stan formy (CTL/ATL/TSB)
2. Gotowość do treningu
3. Ryzyko przetrenowania
4. Trendy w danych wellness

Odpowiadaj po polsku, konkretnie i z konkretnymi rekomendacjami."""

SYSTEM_PROMPT_NUTRITION = """Jesteś dietetykiem sportowym specjalizującym się w żywieniu kolarzy.
Planujesz dietę w oparciu o naukowe podstawy żywienia w sporcie wytrzymałościowym.

Zasady:
- Białko: 1.6-2.0g/kg na odbudowę mięśni
- Węglowodany: 6-10g/kg w ciężkie dni treningowe, 3-5g/kg w dni odpoczynku
- Podczas jazdy: 60-90g węglowodanów/godzinę dla intensywnych wysiłków >90min
- Po treningu: 1.2g/kg węglowodanów + 0.3g/kg białka w ciągu 30min
- Nawodnienie: 500-750ml/godzinę jazdy

Odpowiadaj po polsku. Podawaj konkretne gramature i kalorie."""

SYSTEM_PROMPT_WELLNESS = """Jesteś fizjologiem sportu analizującym trendy zdrowotne zawodnika.
Oceniasz dane wellness: tętno spoczynkowe, HRV (RMSSD/SDNN), wagę, sen, SpO2.

Zwracasz uwagę na:
- Trendy wzrostowe/spadkowe w HRV (wyższe = lepsze)
- Podwyższone tętno spoczynkowe (sygnał zmęczenia)
- Jakość i długość snu
- Zmiany masy ciała
- Niepokojące wzorce wymagające uwagi

Odpowiadaj po polsku z konkretnymi obserwacjami i zaleceniami."""


class AIEngine:
    """OpenAI-powered analysis engine for cycling training data."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    async def _chat(self, system_prompt: str, user_content: str) -> str:
        """Send a chat completion request."""
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.7,
                max_tokens=1500,
            )
            return response.choices[0].message.content or ""
        except Exception:
            logger.exception("OpenAI API call failed")
            raise

    async def summarize_activity(
        self, activity: dict[str, Any], wellness: dict[str, Any] | None = None
    ) -> str:
        """Generate natural language summary of a cycling activity."""
        context = f"Dane aktywności:\n{json.dumps(activity, indent=2, default=str)}"
        if wellness:
            context += (
                f"\n\nDane wellness z dnia treningu:\n{json.dumps(wellness, indent=2, default=str)}"
            )
        context += "\n\nStwórz zwięzłe podsumowanie tego treningu kolarskiego."
        return await self._chat(SYSTEM_PROMPT_SUMMARY, context)

    async def assess_fitness(
        self,
        activities: list[dict[str, Any]],
        wellness_history: list[dict[str, Any]],
        planned: list[dict[str, Any]],
    ) -> str:
        """Assess current fitness based on recent data."""
        context = (
            f"Ostatnie aktywności ({len(activities)}):\n"
            f"{json.dumps(activities[:10], indent=2, default=str)}\n\n"
            f"Historia wellness ({len(wellness_history)} dni):\n"
            f"{json.dumps(wellness_history[:14], indent=2, default=str)}\n\n"
            f"Zaplanowane treningi:\n"
            f"{json.dumps(planned[:7], indent=2, default=str)}\n\n"
            "Oceń aktualną formę zawodnika, gotowość do treningu i daj rekomendacje."
        )
        return await self._chat(SYSTEM_PROMPT_FITNESS, context)

    async def plan_nutrition(
        self,
        weight_kg: float,
        training_load_today: float,
        planned_load_tomorrow: float,
        activity_type: str = "cycling",
    ) -> dict[str, Any]:
        """Generate structured nutrition plan."""
        context = (
            f"Parametry zawodnika:\n"
            f"- Waga: {weight_kg} kg\n"
            f"- Obciążenie treningowe dzisiaj (TSS): {training_load_today}\n"
            f"- Planowane obciążenie jutro (TSS): {planned_load_tomorrow}\n"
            f"- Typ aktywności: {activity_type}\n\n"
            "Stwórz plan żywieniowy na dzisiaj. Odpowiedź MUSI być w formacie JSON:\n"
            '{"calories": X, "protein_g": X, "carbs_g": X, "fat_g": X, '
            '"pre_ride": "opis", "during_ride": "opis", "post_ride": "opis", "notes": "opis"}'
        )
        raw = await self._chat(SYSTEM_PROMPT_NUTRITION, context)

        # Try to parse JSON from response
        try:
            # Find JSON block in response
            start = raw.index("{")
            end = raw.rindex("}") + 1
            parsed: dict[str, Any] = json.loads(raw[start:end])
            return parsed
        except (ValueError, json.JSONDecodeError):
            logger.warning("Failed to parse nutrition JSON, returning raw text")
            return {
                "calories": 0,
                "protein_g": 0,
                "carbs_g": 0,
                "fat_g": 0,
                "notes": raw,
            }

    async def analyze_wellness_trends(self, wellness_data: list[dict[str, Any]]) -> str:
        """Analyze trends in wellness metrics over time."""
        context = (
            f"Dane wellness z ostatnich {len(wellness_data)} dni:\n"
            f"{json.dumps(wellness_data, indent=2, default=str)}\n\n"
            "Przeanalizuj trendy i zgłoś niepokojące wzorce."
        )
        return await self._chat(SYSTEM_PROMPT_WELLNESS, context)
