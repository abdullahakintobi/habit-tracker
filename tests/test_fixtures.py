"""Tests for the predefined habits and their sample tracking data."""

from habit_tracker import analytics, fixtures


def test_seed_creates_five_habits(db):
    habits = fixtures.seed_database(db)
    assert len(habits) == 5
    assert db.count_habits() == 5


def test_seed_is_idempotent(db):
    fixtures.seed_database(db)
    fixtures.seed_database(db)
    assert db.count_habits() == 5


def test_predefined_cover_all_periodicities():
    periods = {h.periodicity.value for h in fixtures.predefined_habits()}
    assert periods == {"daily", "weekly", "monthly"}


def test_predefined_have_at_least_one_daily_and_weekly():
    periods = [h.periodicity.value for h in fixtures.predefined_habits()]
    assert periods.count("daily") >= 1
    assert periods.count("weekly") >= 1


def test_predefined_known_streaks(db):
    """Lock in the streaks produced by the (deterministic) sample data."""
    fixtures.seed_database(db)
    habits = db.get_all_habits()
    streaks = dict(analytics.streaks_by_habit(habits))
    assert streaks["Drink Water"] == 77
    assert streaks["Morning Exercise"] == 6
    assert streaks["Weekly Review"] == 8
    assert streaks["Clean Apartment"] == 24
    assert streaks["Review Monthly Budget"] == 6
    assert analytics.calculate_longest_streak(habits) == 77
