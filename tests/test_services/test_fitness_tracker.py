import pytest

from src.services.fitness_tracker import FitnessTracker


@pytest.fixture
def tracker():
    return FitnessTracker()


# --- calculate_form() tests ---


def test_calculate_form_peak_form(tracker):
    # TSB = CTL - ATL = 80 - 60 = 20 → peak_form (15-25)
    result = tracker.calculate_form(ctl=80, atl=60)
    assert result["tsb"] == 20.0
    assert result["form_status"] == "peak_form"
    assert "Szczytowa forma" in result["form_label"]


def test_calculate_form_fresh(tracker):
    # TSB = 70 - 60 = 10 → fresh (5-15)
    result = tracker.calculate_form(ctl=70, atl=60)
    assert result["tsb"] == 10.0
    assert result["form_status"] == "fresh"
    assert "Świeży" in result["form_label"]


def test_calculate_form_neutral(tracker):
    # TSB = 60 - 62 = -2 → neutral (-10 to 5)
    result = tracker.calculate_form(ctl=60, atl=62)
    assert result["tsb"] == -2.0
    assert result["form_status"] == "neutral"
    assert "Normalny" in result["form_label"]


def test_calculate_form_fatigued(tracker):
    # TSB = 50 - 65 = -15 → fatigued (-25 to -10)
    result = tracker.calculate_form(ctl=50, atl=65)
    assert result["tsb"] == -15.0
    assert result["form_status"] == "fatigued"
    assert "Zmęczenie" in result["form_label"]


def test_calculate_form_very_fatigued(tracker):
    # TSB = 40 - 70 = -30 → very_fatigued (-40 to -25)
    result = tracker.calculate_form(ctl=40, atl=70)
    assert result["tsb"] == -30.0
    assert result["form_status"] == "very_fatigued"
    assert "Silne zmęczenie" in result["form_label"]


def test_calculate_form_overreached(tracker):
    # TSB = 20 - 70 = -50 → overreached (<-40)
    result = tracker.calculate_form(ctl=20, atl=70)
    assert result["tsb"] == -50.0
    assert result["form_status"] == "overreached"
    assert "przetrenowania" in result["form_label"]


def test_calculate_form_returns_ctl_atl(tracker):
    result = tracker.calculate_form(ctl=65.7, atl=58.3)
    assert result["ctl"] == 65.7
    assert result["atl"] == 58.3
    assert result["tsb"] == 7.4


def test_calculate_form_boundary_fresh_peak(tracker):
    # TSB = 15 exactly → peak_form (15 <= 15 < 25)
    result = tracker.calculate_form(ctl=75, atl=60)
    assert result["tsb"] == 15.0
    assert result["form_status"] == "peak_form"


def test_calculate_form_boundary_neutral_fresh(tracker):
    # TSB = 5 exactly → fresh (5 <= 5 < 15)
    result = tracker.calculate_form(ctl=65, atl=60)
    assert result["tsb"] == 5.0
    assert result["form_status"] == "fresh"


# --- assess_readiness() tests ---


def test_assess_readiness_high_score(tracker):
    """Good wellness + good form → high readiness."""
    wellness = {"hrv": 70, "restingHR": 45, "sleepScore": 90}
    form = {"tsb": 20}
    result = tracker.assess_readiness(wellness, form)
    # base 5 + tsb(>15: +2) + hrv(>60: +1) + rhr(<50: +0.5) + sleep(>80: +1) = 9.5
    assert result["readiness_score"] == 9.5
    assert "intensywny" in result["recommendation"]


def test_assess_readiness_low_score(tracker):
    """Poor wellness + bad form → low readiness."""
    wellness = {"hrv": 30, "restingHR": 70, "sleepScore": 40}
    form = {"tsb": -30}
    result = tracker.assess_readiness(wellness, form)
    # base 5 + tsb(<-25: -2) + hrv(<35: -1) + rhr(>65: -1) + sleep(<50: -1) = 1 (clamped)
    assert result["readiness_score"] == 1.0
    assert "odpoczynku" in result["recommendation"]


def test_assess_readiness_moderate_score(tracker):
    """Average wellness → moderate readiness."""
    wellness = {"hrv": 50, "restingHR": 55, "sleepScore": 70}
    form = {"tsb": 0}
    result = tracker.assess_readiness(wellness, form)
    # base 5 + tsb(0: 0) + hrv(50: 0) + rhr(55: 0) + sleep(70: 0) = 5.0
    assert result["readiness_score"] == 5.0
    assert "lżejszy" in result["recommendation"]


def test_assess_readiness_missing_wellness_fields(tracker):
    """Missing wellness data → baseline score with form contribution."""
    wellness = {}
    form = {"tsb": 10}
    result = tracker.assess_readiness(wellness, form)
    # base 5 + tsb(>5: +1) = 6.0
    assert result["readiness_score"] == 6.0
    assert "umiarkowany" in result["recommendation"]


def test_assess_readiness_factors_returned(tracker):
    wellness = {"hrv": 55, "restingHR": 52, "sleepScore": 75}
    form = {"tsb": 3}
    result = tracker.assess_readiness(wellness, form)
    assert result["factors"]["tsb"] == 3
    assert result["factors"]["hrv"] == 55
    assert result["factors"]["resting_hr"] == 52
    assert result["factors"]["sleep_score"] == 75


def test_assess_readiness_hrv_sdnn_fallback(tracker):
    """Uses hrvSDNN when hrv is not present."""
    wellness = {"hrvSDNN": 70, "restingHR": 48, "sleepScore": 85}
    form = {"tsb": 8}
    result = tracker.assess_readiness(wellness, form)
    # base 5 + tsb(>5: +1) + hrv(70>60: +1) + rhr(48<50: +0.5) + sleep(85>80: +1) = 8.5
    assert result["readiness_score"] == 8.5
    assert result["factors"]["hrv"] == 70


def test_assess_readiness_score_clamped_to_10(tracker):
    """Score cannot exceed 10."""
    wellness = {"hrv": 80, "restingHR": 40, "sleepScore": 95}
    form = {"tsb": 20}
    result = tracker.assess_readiness(wellness, form)
    assert result["readiness_score"] <= 10.0


# --- training_recommendation() tests ---


def test_training_recommendation_with_planned_event_high_readiness(tracker):
    form = {"form_status": "fresh"}
    readiness = {"readiness_score": 8}
    planned = {"name": "Sweet Spot Intervals", "icu_training_load": 90}
    result = tracker.training_recommendation(form, readiness, planned_event=planned)
    assert "Sweet Spot Intervals" in result
    assert "TSS ~90" in result
    assert "8/10" in result
    assert "realizuj plan" in result


def test_training_recommendation_with_planned_event_moderate_readiness(tracker):
    form = {"form_status": "neutral"}
    readiness = {"readiness_score": 5}
    planned = {"name": "Tempo Ride", "icu_training_load": 70}
    result = tracker.training_recommendation(form, readiness, planned_event=planned)
    assert "Tempo Ride" in result
    assert "obniżenie intensywności" in result


def test_training_recommendation_with_planned_event_low_readiness(tracker):
    form = {"form_status": "fatigued"}
    readiness = {"readiness_score": 3}
    planned = {"name": "VO2max Intervals", "icu_training_load": 120}
    result = tracker.training_recommendation(form, readiness, planned_event=planned)
    assert "VO2max Intervals" in result
    assert "lżejszy trening" in result or "odpoczynku" in result


def test_training_recommendation_no_plan_overreached(tracker):
    form = {"form_status": "overreached"}
    readiness = {"readiness_score": 2}
    result = tracker.training_recommendation(form, readiness)
    assert "odpoczynku" in result or "lekka jazda Z1" in result


def test_training_recommendation_no_plan_very_fatigued(tracker):
    form = {"form_status": "very_fatigued"}
    readiness = {"readiness_score": 3}
    result = tracker.training_recommendation(form, readiness)
    assert "Z1" in result


def test_training_recommendation_no_plan_fatigued(tracker):
    form = {"form_status": "fatigued"}
    readiness = {"readiness_score": 4}
    result = tracker.training_recommendation(form, readiness)
    assert "Z2" in result


def test_training_recommendation_no_plan_fresh(tracker):
    form = {"form_status": "fresh"}
    readiness = {"readiness_score": 7}
    result = tracker.training_recommendation(form, readiness)
    assert "intensywny" in result


def test_training_recommendation_no_plan_peak_form(tracker):
    form = {"form_status": "peak_form"}
    readiness = {"readiness_score": 9}
    result = tracker.training_recommendation(form, readiness)
    assert "intensywny" in result or "test" in result


def test_training_recommendation_no_plan_neutral(tracker):
    form = {"form_status": "neutral"}
    readiness = {"readiness_score": 5}
    result = tracker.training_recommendation(form, readiness)
    assert "Z2-Z3" in result
