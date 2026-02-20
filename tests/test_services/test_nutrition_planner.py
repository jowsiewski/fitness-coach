import pytest

from src.services.nutrition_planner import NutritionPlanner


@pytest.fixture
def planner():
    return NutritionPlanner()


@pytest.fixture
def base_needs():
    """Base needs for a 75kg, 180cm, 30yo male cyclist."""
    planner = NutritionPlanner()
    return planner.calculate_base_needs(weight_kg=75, height_cm=180, age=30)


# --- calculate_base_needs() tests ---


def test_calculate_base_needs_bmr(planner):
    # BMR = 10*75 + 6.25*180 - 5*30 - 5 = 750 + 1125 - 150 - 5 = 1720
    result = planner.calculate_base_needs(weight_kg=75, height_cm=180, age=30)
    assert result["bmr"] == 1720


def test_calculate_base_needs_tdee(planner):
    # TDEE = BMR * 1.55 = 1720 * 1.55 = 2666
    result = planner.calculate_base_needs(weight_kg=75, height_cm=180, age=30)
    assert result["tdee_base"] == 2666


def test_calculate_base_needs_weight_stored(planner):
    result = planner.calculate_base_needs(weight_kg=75)
    assert result["weight_kg"] == 75


def test_calculate_base_needs_defaults(planner):
    # Default: height=180, age=30 → same as explicit
    result_default = planner.calculate_base_needs(weight_kg=75)
    result_explicit = planner.calculate_base_needs(weight_kg=75, height_cm=180, age=30)
    assert result_default["bmr"] == result_explicit["bmr"]
    assert result_default["tdee_base"] == result_explicit["tdee_base"]


def test_calculate_base_needs_different_weight(planner):
    result = planner.calculate_base_needs(weight_kg=65, height_cm=175, age=25)
    # BMR = 10*65 + 6.25*175 - 5*25 - 5 = 650 + 1093.75 - 125 - 5 = 1613.75 → 1614
    assert result["bmr"] == 1614


# --- plan_for_training_day() tests ---


def test_plan_for_training_day_moderate_load(planner, base_needs):
    """TSS 80 → moderate day macros."""
    result = planner.plan_for_training_day(base_needs, training_load=80, duration_hours=2.0)
    # Moderate: carbs=6g/kg=450, protein=1.7g/kg=127.5
    assert result["carbs_g"] == 450
    assert result["protein_g"] == 128  # round(75*1.7)
    assert result["training_load"] == 80
    assert result["duration_hours"] == 2.0


def test_plan_for_training_day_high_load(planner, base_needs):
    """TSS 120 → hard day macros."""
    result = planner.plan_for_training_day(base_needs, training_load=120, duration_hours=3.0)
    # Hard: carbs=7g/kg=525, protein=1.8g/kg=135
    assert result["carbs_g"] == 525
    assert result["protein_g"] == 135


def test_plan_for_training_day_very_hard_load(planner, base_needs):
    """TSS 180 → very hard day macros."""
    result = planner.plan_for_training_day(base_needs, training_load=180, duration_hours=4.0)
    # Very hard: carbs=9g/kg=675, protein=2.0g/kg=150
    assert result["carbs_g"] == 675
    assert result["protein_g"] == 150


def test_plan_for_training_day_easy_load(planner, base_needs):
    """TSS 30 → easy day macros."""
    result = planner.plan_for_training_day(base_needs, training_load=30, duration_hours=1.0)
    # Easy: carbs=5g/kg=375, protein=1.6g/kg=120
    assert result["carbs_g"] == 375
    assert result["protein_g"] == 120


def test_plan_for_training_day_on_bike_carbs_long_hard(planner, base_needs):
    """Long hard ride → 80g carbs/hour."""
    result = planner.plan_for_training_day(base_needs, training_load=120, duration_hours=3.0)
    assert result["carbs_per_hour_riding"] == 80


def test_plan_for_training_day_on_bike_carbs_long_moderate(planner, base_needs):
    """Long moderate ride → 60g carbs/hour."""
    result = planner.plan_for_training_day(base_needs, training_load=80, duration_hours=2.0)
    assert result["carbs_per_hour_riding"] == 60


def test_plan_for_training_day_on_bike_carbs_medium(planner, base_needs):
    """1-1.5h ride → 40g carbs/hour."""
    result = planner.plan_for_training_day(base_needs, training_load=50, duration_hours=1.25)
    assert result["carbs_per_hour_riding"] == 40


def test_plan_for_training_day_on_bike_carbs_short(planner, base_needs):
    """<1h ride → 0g carbs/hour."""
    result = planner.plan_for_training_day(base_needs, training_load=30, duration_hours=0.75)
    assert result["carbs_per_hour_riding"] == 0


def test_plan_for_training_day_hydration(planner, base_needs):
    result = planner.plan_for_training_day(base_needs, training_load=80, duration_hours=2.5)
    assert result["hydration_ml"] == 1500  # 2.5 * 600


def test_plan_for_training_day_has_fat(planner, base_needs):
    result = planner.plan_for_training_day(base_needs, training_load=80, duration_hours=2.0)
    assert result["fat_g"] > 0


def test_plan_for_training_day_calories_computed(planner, base_needs):
    result = planner.plan_for_training_day(base_needs, training_load=80, duration_hours=2.0)
    # calories ≈ protein*4 + carbs*4 + fat*9 (rounding differences allowed)
    expected = result["protein_g"] * 4 + result["carbs_g"] * 4 + result["fat_g"] * 9
    assert abs(result["calories"] - round(expected)) <= 10


# --- plan_for_rest_day() tests ---


def test_plan_for_rest_day_lower_carbs_than_training(planner, base_needs):
    rest = planner.plan_for_rest_day(base_needs)
    training = planner.plan_for_training_day(base_needs, training_load=80, duration_hours=2.0)
    assert rest["carbs_g"] < training["carbs_g"]


def test_plan_for_rest_day_correct_macros(planner, base_needs):
    result = planner.plan_for_rest_day(base_needs)
    # protein = 75*1.6 = 120, carbs = 75*3.5 = 262.5 → 262
    assert result["protein_g"] == 120
    assert result["carbs_g"] == 262  # round(75*3.5)


def test_plan_for_rest_day_zero_riding_nutrition(planner, base_needs):
    result = planner.plan_for_rest_day(base_needs)
    assert result["carbs_per_hour_riding"] == 0
    assert result["training_load"] == 0
    assert result["duration_hours"] == 0


def test_plan_for_rest_day_hydration(planner, base_needs):
    result = planner.plan_for_rest_day(base_needs)
    assert result["hydration_ml"] == 2000


def test_plan_for_rest_day_has_notes(planner, base_needs):
    result = planner.plan_for_rest_day(base_needs)
    assert "odpoczynku" in result["notes"]


# --- pre_ride_meal() tests ---


def test_pre_ride_meal_long_ride(planner):
    """Duration >3h → large pre-ride meal."""
    result = planner.pre_ride_meal(duration_hours=4.0)
    assert result["carbs_g"] == 150
    assert result["protein_g"] == 20
    assert result["timing"] == "3h przed jazdą"


def test_pre_ride_meal_medium_ride(planner):
    """Duration 1.5-3h → medium pre-ride meal."""
    result = planner.pre_ride_meal(duration_hours=2.0)
    assert result["carbs_g"] == 100
    assert result["protein_g"] == 15
    assert result["timing"] == "2h przed jazdą"


def test_pre_ride_meal_short_ride(planner):
    """Duration <1.5h → small pre-ride snack."""
    result = planner.pre_ride_meal(duration_hours=1.0)
    assert result["carbs_g"] == 50
    assert result["protein_g"] == 5
    assert result["timing"] == "1h przed jazdą"


def test_pre_ride_meal_has_examples(planner):
    result = planner.pre_ride_meal(duration_hours=2.5)
    assert "examples" in result
    assert len(result["examples"]) > 0


# --- during_ride_nutrition() tests ---


def test_during_ride_short(planner):
    """<=1h → water only."""
    result = planner.during_ride_nutrition(duration_hours=0.75)
    assert result["carbs_per_hour"] == 0
    assert result["hydration_ml_per_hour"] == 400


def test_during_ride_medium_moderate(planner):
    """1-2h moderate → 40g/h."""
    result = planner.during_ride_nutrition(duration_hours=1.5, intensity="moderate")
    assert result["carbs_per_hour"] == 40
    assert result["hydration_ml_per_hour"] == 500


def test_during_ride_medium_high(planner):
    """1-2h high intensity → 60g/h."""
    result = planner.during_ride_nutrition(duration_hours=1.5, intensity="high")
    assert result["carbs_per_hour"] == 60
    assert result["hydration_ml_per_hour"] == 500


def test_during_ride_long_moderate(planner):
    """>2h moderate → 70g/h."""
    result = planner.during_ride_nutrition(duration_hours=3.0, intensity="moderate")
    assert result["carbs_per_hour"] == 70
    assert result["hydration_ml_per_hour"] == 600


def test_during_ride_long_high(planner):
    """>2h high intensity → 90g/h."""
    result = planner.during_ride_nutrition(duration_hours=3.0, intensity="high")
    assert result["carbs_per_hour"] == 90
    assert result["hydration_ml_per_hour"] == 600


def test_during_ride_has_examples_for_long(planner):
    result = planner.during_ride_nutrition(duration_hours=3.0)
    assert "examples" in result


def test_during_ride_boundary_1h(planner):
    """Exactly 1h → water only."""
    result = planner.during_ride_nutrition(duration_hours=1.0)
    assert result["carbs_per_hour"] == 0


def test_during_ride_boundary_2h(planner):
    """Exactly 2h → medium tier."""
    result = planner.during_ride_nutrition(duration_hours=2.0, intensity="moderate")
    assert result["carbs_per_hour"] == 40


# --- post_ride_recovery() tests ---


def test_post_ride_recovery_heavy_load(planner):
    """TSS >150 → urgent recovery."""
    result = planner.post_ride_recovery(training_load=180, duration_hours=4.0)
    assert result["carbs_g"] == 90  # round(75*1.2)
    assert result["protein_g"] == 22  # round(75*0.3)
    assert "szybkie uzupełnienie" in result["notes"]


def test_post_ride_recovery_moderate_load(planner):
    """TSS 80-150 → solid recovery."""
    result = planner.post_ride_recovery(training_load=100, duration_hours=2.5)
    assert result["carbs_g"] == 90
    assert result["protein_g"] == 22
    assert "solidny posiłek" in result["notes"]


def test_post_ride_recovery_light_load(planner):
    """TSS <80 → normal meal."""
    result = planner.post_ride_recovery(training_load=40, duration_hours=1.0)
    assert result["carbs_g"] == 90
    assert result["protein_g"] == 22
    assert "normalny posiłek" in result["notes"]


def test_post_ride_recovery_timing(planner):
    result = planner.post_ride_recovery(training_load=100, duration_hours=2.0)
    assert "30 minut" in result["timing"]


def test_post_ride_recovery_hydration(planner):
    result = planner.post_ride_recovery(training_load=100, duration_hours=3.0)
    assert result["hydration_ml"] == 1500  # 3.0 * 500


def test_post_ride_recovery_has_examples(planner):
    result = planner.post_ride_recovery(training_load=100, duration_hours=2.0)
    assert "examples" in result
    assert len(result["examples"]) > 0
