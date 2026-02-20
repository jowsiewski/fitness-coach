import pytest

from src.services.activity_analyzer import ActivityAnalyzer


@pytest.fixture
def analyzer():
    return ActivityAnalyzer()


@pytest.fixture
def sample_activity():
    return {
        "id": "act_12345",
        "name": "Morning Ride",
        "start_date_local": "2025-02-15T08:00:00",
        "type": "Ride",
        "moving_time": 3600,  # 60 min
        "distance": 30000,  # 30 km
        "icu_training_load": 75.0,
        "icu_ftp": 250,
        "average_watts": 200,
        "icu_weighted_avg_watts": 220,
        "max_watts": 450,
        "average_heartrate": 145,
        "max_heartrate": 175,
        "average_cadence": 88,
        "calories": 650,
        "total_elevation_gain": 320,
    }


# --- analyze() tests ---


def test_analyze_returns_key_metrics(analyzer, sample_activity):
    result = analyzer.analyze(sample_activity)
    assert result["id"] == "act_12345"
    assert result["name"] == "Morning Ride"
    assert result["date"] == "2025-02-15T08:00:00"
    assert result["type"] == "Ride"


def test_analyze_calculates_duration(analyzer, sample_activity):
    result = analyzer.analyze(sample_activity)
    assert result["duration_min"] == 60.0
    assert result["duration_h"] == 1.0


def test_analyze_converts_distance_to_km(analyzer, sample_activity):
    result = analyzer.analyze(sample_activity)
    assert result["distance_km"] == 30.0


def test_analyze_returns_tss(analyzer, sample_activity):
    result = analyzer.analyze(sample_activity)
    assert result["tss"] == 75.0


def test_analyze_calculates_intensity_factor(analyzer, sample_activity):
    result = analyzer.analyze(sample_activity)
    # IF = NP / FTP = 220 / 250 = 0.88
    assert result["intensity_factor"] == 0.88


def test_analyze_returns_power_metrics(analyzer, sample_activity):
    result = analyzer.analyze(sample_activity)
    assert result["avg_power"] == 200
    assert result["normalized_power"] == 220
    assert result["max_power"] == 450
    assert result["ftp"] == 250


def test_analyze_returns_hr_and_cadence(analyzer, sample_activity):
    result = analyzer.analyze(sample_activity)
    assert result["avg_hr"] == 145
    assert result["max_hr"] == 175
    assert result["avg_cadence"] == 88


def test_analyze_returns_calories_and_elevation(analyzer, sample_activity):
    result = analyzer.analyze(sample_activity)
    assert result["calories"] == 650
    assert result["elevation_m"] == 320


def test_analyze_power_zone_assigned(analyzer, sample_activity):
    result = analyzer.analyze(sample_activity)
    # 200/250 = 80% → Z3 Tempo
    assert result["power_zone"] == "Z3 Tempo"


def test_analyze_handles_zero_ftp(analyzer, sample_activity):
    sample_activity["icu_ftp"] = 0
    result = analyzer.analyze(sample_activity)
    assert result["intensity_factor"] == 0
    assert result["power_zone"] == "N/A"


def test_analyze_handles_none_values(analyzer):
    activity = {
        "id": "act_empty",
        "moving_time": None,
        "distance": None,
        "icu_training_load": None,
        "icu_ftp": None,
        "average_watts": None,
        "icu_weighted_avg_watts": None,
    }
    result = analyzer.analyze(activity)
    assert result["duration_min"] == 0.0
    assert result["distance_km"] == 0.0
    assert result["tss"] == 0.0
    assert result["intensity_factor"] == 0
    assert result["power_zone"] == "N/A"


# --- _power_zone() tests ---


def test_power_zone_z1_active_recovery():
    # <55% FTP → Z1
    assert ActivityAnalyzer._power_zone(100, 250) == "Z1 Aktywny wypoczynek"


def test_power_zone_z2_endurance():
    # 55-75% FTP → Z2
    assert ActivityAnalyzer._power_zone(150, 250) == "Z2 Wytrzymałość"


def test_power_zone_z3_tempo():
    # 75-90% FTP → Z3
    assert ActivityAnalyzer._power_zone(200, 250) == "Z3 Tempo"


def test_power_zone_z4_threshold():
    # 90-105% FTP → Z4
    assert ActivityAnalyzer._power_zone(240, 250) == "Z4 Próg"


def test_power_zone_z5_vo2max():
    # 105-120% FTP → Z5
    assert ActivityAnalyzer._power_zone(280, 250) == "Z5 VO2max"


def test_power_zone_z6_anaerobic():
    # >=120% FTP → Z6
    assert ActivityAnalyzer._power_zone(310, 250) == "Z6 Anaerobowy"


def test_power_zone_boundary_z1_z2():
    # Exactly 55% → Z2
    assert ActivityAnalyzer._power_zone(137.5, 250) == "Z2 Wytrzymałość"


def test_power_zone_boundary_z4_z5():
    # Exactly 105% → Z5
    assert ActivityAnalyzer._power_zone(262.5, 250) == "Z5 VO2max"


# --- compare_to_plan() tests ---


def test_compare_to_plan_high_compliance(analyzer):
    actual = {"icu_training_load": 95, "moving_time": 3500}
    planned = {"icu_training_load": 100, "moving_time": 3600}
    result = analyzer.compare_to_plan(actual, planned)
    # load: 95%, time: 97.2%, avg: 96.1%
    assert result["overall_compliance_pct"] >= 90
    assert "zgodnie z planem" in result["notes"]


def test_compare_to_plan_partial_compliance(analyzer):
    actual = {"icu_training_load": 75, "moving_time": 2800}
    planned = {"icu_training_load": 100, "moving_time": 3600}
    result = analyzer.compare_to_plan(actual, planned)
    # load: 75%, time: 77.8%, avg: 76.4%
    assert 70 <= result["overall_compliance_pct"] < 90
    assert "częściowo" in result["notes"]


def test_compare_to_plan_low_compliance(analyzer):
    actual = {"icu_training_load": 30, "moving_time": 1800}
    planned = {"icu_training_load": 100, "moving_time": 3600}
    result = analyzer.compare_to_plan(actual, planned)
    # load: 30%, time: 50%, avg: 40%
    assert result["overall_compliance_pct"] < 70
    assert "odchylenie" in result["notes"]


def test_compare_to_plan_zero_planned(analyzer):
    actual = {"icu_training_load": 50, "moving_time": 1800}
    planned = {"icu_training_load": 0, "moving_time": 0}
    result = analyzer.compare_to_plan(actual, planned)
    assert result["load_compliance_pct"] == 0
    assert result["time_compliance_pct"] == 0


def test_compare_to_plan_returns_all_fields(analyzer):
    actual = {"icu_training_load": 80, "moving_time": 3000}
    planned = {"icu_training_load": 100, "moving_time": 3600}
    result = analyzer.compare_to_plan(actual, planned)
    assert "load_compliance_pct" in result
    assert "time_compliance_pct" in result
    assert "overall_compliance_pct" in result
    assert "notes" in result


# --- weekly_summary() tests ---


def test_weekly_summary_aggregates_activities(analyzer):
    activities = [
        {
            "icu_training_load": 80,
            "moving_time": 3600,
            "distance": 30000,
            "total_elevation_gain": 400,
            "calories": 700,
            "icu_intensity": 85,
        },
        {
            "icu_training_load": 60,
            "moving_time": 5400,
            "distance": 50000,
            "total_elevation_gain": 600,
            "calories": 900,
            "icu_intensity": 72,
        },
        {
            "icu_training_load": 100,
            "moving_time": 7200,
            "distance": 70000,
            "total_elevation_gain": 800,
            "calories": 1200,
            "icu_intensity": 90,
        },
    ]
    result = analyzer.weekly_summary(activities)
    assert result["activity_count"] == 3
    assert result["rest_days"] == 4
    assert result["total_tss"] == 240.0
    assert result["total_hours"] == 4.5  # (3600+5400+7200)/3600
    assert result["total_km"] == 150.0
    assert result["total_elevation_m"] == 1800
    assert result["total_calories"] == 2800
    # avg intensity = (85+72+90)/3 = 82.33 → /100 = 0.82
    assert result["avg_intensity_factor"] == 0.82


def test_weekly_summary_empty_activities(analyzer):
    result = analyzer.weekly_summary([])
    assert result["activity_count"] == 0
    assert result["rest_days"] == 7
    assert result["total_tss"] == 0.0
    assert result["total_hours"] == 0.0
    assert result["total_km"] == 0.0
    assert result["avg_intensity_factor"] == 0


def test_weekly_summary_single_activity(analyzer):
    activities = [
        {
            "icu_training_load": 50,
            "moving_time": 1800,
            "distance": 15000,
            "total_elevation_gain": 100,
            "calories": 300,
            "icu_intensity": 65,
        },
    ]
    result = analyzer.weekly_summary(activities)
    assert result["activity_count"] == 1
    assert result["rest_days"] == 6
    assert result["total_tss"] == 50.0
    assert result["total_hours"] == 0.5


def test_weekly_summary_handles_none_intensity(analyzer):
    activities = [
        {
            "icu_training_load": 50,
            "moving_time": 1800,
            "distance": 15000,
            "total_elevation_gain": 100,
            "calories": 300,
            "icu_intensity": None,
        },
    ]
    result = analyzer.weekly_summary(activities)
    assert result["avg_intensity_factor"] == 0
