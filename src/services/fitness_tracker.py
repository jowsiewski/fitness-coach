import logging
from typing import Any

logger = logging.getLogger(__name__)

# TSB thresholds for form assessment
FORM_THRESHOLDS = {
    "peak_form": (15, 25),  # TSB 15-25: ideal race form
    "fresh": (5, 15),  # TSB 5-15: fresh, ready for quality work
    "neutral": (-10, 5),  # TSB -10 to 5: normal training
    "fatigued": (-25, -10),  # TSB -25 to -10: accumulated fatigue
    "very_fatigued": (-40, -25),  # TSB -40 to -25: heavy training block
    "overreached": (-100, -40),  # TSB < -40: risk of overtraining
}


class FitnessTracker:
    """Tracks and assesses cycling fitness using PMC model (CTL/ATL/TSB)."""

    def calculate_form(self, ctl: float, atl: float) -> dict[str, Any]:
        """Calculate Training Stress Balance and classify form status."""
        tsb = ctl - atl

        form_status = "neutral"
        for status, (low, high) in FORM_THRESHOLDS.items():
            if low <= tsb < high:
                form_status = status
                break

        status_labels = {
            "peak_form": "🏆 Szczytowa forma",
            "fresh": "✅ Świeży, gotowy do treningu",
            "neutral": "➡️ Normalny stan treningowy",
            "fatigued": "⚠️ Zmęczenie — rozważ lżejszy trening",
            "very_fatigued": "🔶 Silne zmęczenie — potrzebna regeneracja",
            "overreached": "🔴 Ryzyko przetrenowania — wymagany odpoczynek",
        }

        return {
            "ctl": round(ctl, 1),
            "atl": round(atl, 1),
            "tsb": round(tsb, 1),
            "form_status": form_status,
            "form_label": status_labels.get(form_status, form_status),
        }

    def assess_readiness(self, wellness: dict[str, Any], form: dict[str, Any]) -> dict[str, Any]:
        """Combine wellness and form data into a readiness score (1-10)."""
        score = 5.0  # baseline

        # TSB contribution (±2 points)
        tsb = form.get("tsb", 0)
        if tsb > 15:
            score += 2
        elif tsb > 5:
            score += 1
        elif tsb < -25:
            score -= 2
        elif tsb < -10:
            score -= 1

        # HRV contribution (±1 point) — higher is better
        hrv = wellness.get("hrv") or wellness.get("hrvSDNN")
        if hrv is not None:
            # Simplified: assume baseline HRV ~50ms RMSSD for cyclist
            if hrv > 60:
                score += 1
            elif hrv < 35:
                score -= 1

        # Resting HR (±1 point) — lower is better
        rhr = wellness.get("restingHR")
        if rhr is not None:
            if rhr < 50:
                score += 0.5
            elif rhr > 65:
                score -= 1

        # Sleep (±1 point)
        sleep_score = wellness.get("sleepScore")
        if sleep_score is not None:
            if sleep_score > 80:
                score += 1
            elif sleep_score < 50:
                score -= 1

        score = max(1.0, min(10.0, score))

        if score >= 8:
            recommendation = "Gotowy na intensywny trening 💪"
        elif score >= 6:
            recommendation = "Dobry dzień na trening umiarkowany"
        elif score >= 4:
            recommendation = "Rozważ lżejszy trening lub aktywny odpoczynek"
        else:
            recommendation = "Zalecany dzień odpoczynku 🛌"

        return {
            "readiness_score": round(score, 1),
            "recommendation": recommendation,
            "factors": {
                "tsb": form.get("tsb", 0),
                "hrv": hrv,
                "resting_hr": rhr,
                "sleep_score": sleep_score,
            },
        }

    def training_recommendation(
        self,
        form: dict[str, Any],
        readiness: dict[str, Any],
        planned_event: dict[str, Any] | None = None,
    ) -> str:
        """Generate training recommendation for today."""
        score = readiness.get("readiness_score", 5)
        form_status = form.get("form_status", "neutral")

        if planned_event:
            planned_load = planned_event.get("icu_training_load", 0) or 0
            planned_name = planned_event.get("name", "Zaplanowany trening")

            if score >= 7:
                return (
                    f"📋 Plan: {planned_name} (TSS ~{planned_load})\n"
                    f"Gotowość: {score}/10 — realizuj plan zgodnie z założeniami."
                )
            elif score >= 4:
                return (
                    f"📋 Plan: {planned_name} (TSS ~{planned_load})\n"
                    f"Gotowość: {score}/10 — rozważ obniżenie intensywności o 10-15%."
                )
            else:
                return (
                    f"📋 Plan: {planned_name} (TSS ~{planned_load})\n"
                    f"Gotowość: {score}/10 — ⚠️ Zalecam zamianę na lżejszy trening "
                    f"lub dzień odpoczynku."
                )

        # No planned event
        if form_status in ("overreached", "very_fatigued"):
            return f"Gotowość: {score}/10 — Dzień odpoczynku lub bardzo lekka jazda Z1 (30-45min)."
        elif form_status == "fatigued":
            return f"Gotowość: {score}/10 — Lekka jazda Z2 (60-90min) lub aktywny odpoczynek."
        elif form_status in ("fresh", "peak_form"):
            return f"Gotowość: {score}/10 — Dobry dzień na intensywny trening lub test!"
        else:
            return f"Gotowość: {score}/10 — Normalny dzień treningowy. Z2-Z3 wg uznania."
