import logging
from typing import Any

logger = logging.getLogger(__name__)


class NutritionPlanner:
    """Cycling-specific nutrition planning based on training load.

    Based on sports nutrition science:
    - Protein: 1.6-2.0g/kg for recovery
    - Carbs: 6-10g/kg on hard days, 3-5g/kg on rest days
    - During ride: 60-90g carbs/hour for intense >90min
    - Post-ride: 1.2g/kg carbs + 0.3g/kg protein within 30min
    """

    def calculate_base_needs(
        self,
        weight_kg: float,
        height_cm: float = 180,
        age: int = 30,
    ) -> dict[str, Any]:
        """Calculate BMR and TDEE using Mifflin-St Jeor (male cyclist)."""
        # BMR = 10 * weight(kg) + 6.25 * height(cm) - 5 * age - 5 (male)
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 5

        # Activity factor for cyclist (moderately active baseline)
        tdee = bmr * 1.55

        return {
            "bmr": round(bmr),
            "tdee_base": round(tdee),
            "weight_kg": weight_kg,
        }

    def plan_for_training_day(
        self,
        base_needs: dict[str, Any],
        training_load: float,
        duration_hours: float,
    ) -> dict[str, Any]:
        """Calculate nutrition for a training day based on TSS and duration."""
        weight = base_needs["weight_kg"]
        tdee = base_needs["tdee_base"]

        # Extra calories from training (~4-5 kcal per TSS point)
        training_calories = training_load * 4.5
        total_calories = tdee + training_calories

        # Macros based on training intensity
        if training_load > 150:  # Very hard day
            carbs_g_per_kg = 9.0
            protein_g_per_kg = 2.0
        elif training_load > 100:  # Hard day
            carbs_g_per_kg = 7.0
            protein_g_per_kg = 1.8
        elif training_load > 50:  # Moderate day
            carbs_g_per_kg = 6.0
            protein_g_per_kg = 1.7
        else:  # Easy day
            carbs_g_per_kg = 5.0
            protein_g_per_kg = 1.6

        protein_g = weight * protein_g_per_kg
        carbs_g = weight * carbs_g_per_kg
        protein_cal = protein_g * 4
        carbs_cal = carbs_g * 4
        fat_cal = max(total_calories - protein_cal - carbs_cal, weight * 0.8 * 9)
        fat_g = fat_cal / 9

        # Recalculate total
        total_calories = protein_cal + carbs_cal + fat_cal

        # On-bike nutrition
        if duration_hours > 1.5:
            carbs_per_hour = 80 if training_load > 100 else 60
        elif duration_hours > 1:
            carbs_per_hour = 40
        else:
            carbs_per_hour = 0

        hydration_ml = int(duration_hours * 600)

        return {
            "calories": round(total_calories),
            "protein_g": round(protein_g),
            "carbs_g": round(carbs_g),
            "fat_g": round(fat_g),
            "carbs_per_hour_riding": carbs_per_hour,
            "hydration_ml": hydration_ml,
            "training_load": training_load,
            "duration_hours": duration_hours,
        }

    def plan_for_rest_day(self, base_needs: dict[str, Any]) -> dict[str, Any]:
        """Nutrition plan for rest day — lower carb, maintain protein."""
        weight = base_needs["weight_kg"]
        tdee = base_needs["tdee_base"]

        protein_g = weight * 1.6
        carbs_g = weight * 3.5
        protein_cal = protein_g * 4
        carbs_cal = carbs_g * 4
        fat_cal = max(tdee - protein_cal - carbs_cal, weight * 1.0 * 9)
        fat_g = fat_cal / 9

        total_calories = protein_cal + carbs_cal + fat_cal

        return {
            "calories": round(total_calories),
            "protein_g": round(protein_g),
            "carbs_g": round(carbs_g),
            "fat_g": round(fat_g),
            "carbs_per_hour_riding": 0,
            "hydration_ml": 2000,
            "training_load": 0,
            "duration_hours": 0,
            "notes": "Dzień odpoczynku — skup się na nawodnieniu i jakości posiłków.",
        }

    def pre_ride_meal(self, duration_hours: float, intensity: str = "moderate") -> dict[str, Any]:
        """Pre-ride meal recommendation."""
        if duration_hours > 3:
            return {
                "timing": "3h przed jazdą",
                "carbs_g": 150,
                "protein_g": 20,
                "fat_g": 10,
                "examples": "Owsianka z bananem i miodem, tosty z dżemem, ryż z kurczakiem",
                "notes": "Unikaj dużej ilości błonnika i tłuszczu. Dojedz 200-300ml napoju.",
            }
        elif duration_hours > 1.5:
            return {
                "timing": "2h przed jazdą",
                "carbs_g": 100,
                "protein_g": 15,
                "fat_g": 5,
                "examples": "Banana + batonik energetyczny, kanapka z dżemem",
                "notes": "Lekki, łatwostrawny posiłek bogatyw w węglowodany.",
            }
        else:
            return {
                "timing": "1h przed jazdą",
                "carbs_g": 50,
                "protein_g": 5,
                "fat_g": 2,
                "examples": "Banan, żel energetyczny, napój izotoniczny",
                "notes": "Mały przekąska — nie jedz za dużo przed krótkim treningiem.",
            }

    def during_ride_nutrition(
        self, duration_hours: float, intensity: str = "moderate"
    ) -> dict[str, Any]:
        """On-bike nutrition recommendations."""
        if duration_hours <= 1:
            return {
                "carbs_per_hour": 0,
                "hydration_ml_per_hour": 400,
                "notes": "Woda wystarczy. Opcjonalnie napój izotoniczny.",
            }
        elif duration_hours <= 2:
            carbs = 60 if intensity == "high" else 40
            return {
                "carbs_per_hour": carbs,
                "hydration_ml_per_hour": 500,
                "examples": "Żele, batony energetyczne, napój z maltodekstryną",
                "notes": f"Cel: {carbs}g węglowodanów/h. Pij regularnie co 15-20min.",
            }
        else:
            carbs = 90 if intensity == "high" else 70
            return {
                "carbs_per_hour": carbs,
                "hydration_ml_per_hour": 600,
                "examples": "Mix żeli + batonów + napój. Fruktoza + glukoza (stosunek 1:0.8)",
                "notes": (
                    f"Cel: {carbs}g/h (mieszanka glukozy i fruktozy). "
                    "Zacznij jeść od pierwszej godziny. Elektrolity w napoju."
                ),
            }

    def post_ride_recovery(self, training_load: float, duration_hours: float) -> dict[str, Any]:
        """Post-ride recovery nutrition (within 30min window)."""
        # Assume 75kg cyclist as default
        weight = 75.0

        carbs_g = weight * 1.2
        protein_g = weight * 0.3

        if training_load > 150:
            notes = (
                "Ciężki trening — priorytet: szybkie uzupełnienie glikogenu. "
                "Posiłek bogaty w węglowodany + białko w ciągu 30min."
            )
        elif training_load > 80:
            notes = "Umiarkowany trening — solidny posiłek regeneracyjny w ciągu 60min."
        else:
            notes = "Lekki trening — normalny posiłek wystarczy."

        return {
            "timing": "W ciągu 30 minut po treningu",
            "carbs_g": round(carbs_g),
            "protein_g": round(protein_g),
            "examples": (
                "Shake proteinowy z bananem i owsianką, "
                "ryż z kurczakiem i warzywami, "
                "jogurt grecki z muesli i owocami"
            ),
            "hydration_ml": int(duration_hours * 500),
            "notes": notes,
        }
