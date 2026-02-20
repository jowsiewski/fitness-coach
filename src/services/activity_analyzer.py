import logging
from typing import Any

logger = logging.getLogger(__name__)


class ActivityAnalyzer:
    """Analyzes cycling activities and extracts key metrics."""

    def analyze(self, activity: dict[str, Any]) -> dict[str, Any]:
        """Extract and compute key metrics from an activity."""
        ftp = activity.get("icu_ftp", 0) or 0
        avg_watts = activity.get("average_watts", 0) or 0
        np_watts = activity.get("icu_weighted_avg_watts", 0) or 0
        moving_time_s = activity.get("moving_time", 0) or 0
        tss = activity.get("icu_training_load", 0) or 0

        # Intensity Factor
        intensity_factor = (np_watts / ftp) if ftp > 0 else 0

        # Power zone (based on avg watts)
        zone = self._power_zone(avg_watts, ftp) if ftp > 0 else "N/A"

        return {
            "id": activity.get("id"),
            "name": activity.get("name", "Bez nazwy"),
            "date": activity.get("start_date_local", ""),
            "type": activity.get("type", "Ride"),
            "duration_min": round(moving_time_s / 60, 1),
            "duration_h": round(moving_time_s / 3600, 2),
            "distance_km": round((activity.get("distance", 0) or 0) / 1000, 1),
            "tss": round(tss, 1),
            "intensity_factor": round(intensity_factor, 2),
            "avg_power": round(avg_watts, 0),
            "normalized_power": round(np_watts, 0),
            "max_power": activity.get("max_watts", 0),
            "avg_hr": activity.get("average_heartrate", 0),
            "max_hr": activity.get("max_heartrate", 0),
            "avg_cadence": activity.get("average_cadence", 0),
            "calories": activity.get("calories", 0),
            "elevation_m": activity.get("total_elevation_gain", 0),
            "ftp": ftp,
            "power_zone": zone,
        }

    def compare_to_plan(self, activity: dict[str, Any], planned: dict[str, Any]) -> dict[str, Any]:
        """Compare actual activity vs planned workout."""
        actual_load = activity.get("icu_training_load", 0) or 0
        planned_load = planned.get("icu_training_load", 0) or 0
        actual_time = activity.get("moving_time", 0) or 0
        planned_time = planned.get("moving_time", 0) or 0

        load_pct = (actual_load / planned_load * 100) if planned_load > 0 else 0
        time_pct = (actual_time / planned_time * 100) if planned_time > 0 else 0

        compliance = (load_pct + time_pct) / 2

        if compliance >= 90:
            notes = "Trening zrealizowany zgodnie z planem ✅"
        elif compliance >= 70:
            notes = "Trening częściowo zrealizowany ⚠️"
        else:
            notes = "Znaczne odchylenie od planu ❌"

        return {
            "load_compliance_pct": round(load_pct, 1),
            "time_compliance_pct": round(time_pct, 1),
            "overall_compliance_pct": round(compliance, 1),
            "notes": notes,
        }

    def weekly_summary(self, activities: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate weekly statistics."""
        total_tss = 0.0
        total_time_s = 0
        total_distance = 0.0
        total_elevation = 0.0
        total_calories = 0.0
        intensities: list[float] = []

        for a in activities:
            total_tss += a.get("icu_training_load", 0) or 0
            total_time_s += a.get("moving_time", 0) or 0
            total_distance += a.get("distance", 0) or 0
            total_elevation += a.get("total_elevation_gain", 0) or 0
            total_calories += a.get("calories", 0) or 0
            if_val = a.get("icu_intensity", 0) or 0
            if if_val > 0:
                intensities.append(if_val)

        avg_if = sum(intensities) / len(intensities) if intensities else 0
        activity_days = len(activities)
        rest_days = 7 - activity_days

        return {
            "activity_count": activity_days,
            "rest_days": max(rest_days, 0),
            "total_tss": round(total_tss, 1),
            "total_hours": round(total_time_s / 3600, 1),
            "total_km": round(total_distance / 1000, 1),
            "total_elevation_m": round(total_elevation, 0),
            "total_calories": round(total_calories, 0),
            "avg_intensity_factor": round(avg_if / 100, 2),  # ICU stores as percentage
        }

    @staticmethod
    def _power_zone(watts: float, ftp: float) -> str:
        """Determine Coggan power zone."""
        pct = (watts / ftp) * 100
        if pct < 55:
            return "Z1 Aktywny wypoczynek"
        elif pct < 75:
            return "Z2 Wytrzymałość"
        elif pct < 90:
            return "Z3 Tempo"
        elif pct < 105:
            return "Z4 Próg"
        elif pct < 120:
            return "Z5 VO2max"
        else:
            return "Z6 Anaerobowy"
