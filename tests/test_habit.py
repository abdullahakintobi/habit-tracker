"""Tests for the object-oriented core: ``Habit`` and ``Periodicity``."""

from datetime import datetime

import pytest

from habit_tracker.habit import Habit, Periodicity


def test_create_valid_habit():
    habit = Habit("Drink Water", "daily", "Stay hydrated")
    assert habit.name == "Drink Water"
    assert habit.periodicity is Periodicity.DAILY
    assert habit.description == "Stay hydrated"
    assert habit.id is None
    assert habit.completion_dates == []


def test_name_and_description_are_stripped():
    habit = Habit("  Water  ", "daily", "  hydrate  ")
    assert habit.name == "Water"
    assert habit.description == "hydrate"


def test_empty_name_raises():
    with pytest.raises(ValueError):
        Habit("   ", "daily")


def test_invalid_periodicity_raises():
    with pytest.raises(ValueError):
        Habit("Water", "yearly")


@pytest.mark.parametrize(
    "value,expected",
    [
        ("daily", Periodicity.DAILY),
        ("WEEKLY", Periodicity.WEEKLY),
        (" Monthly ", Periodicity.MONTHLY),
        (Periodicity.DAILY, Periodicity.DAILY),
    ],
)
def test_periodicity_from_value(value, expected):
    assert Periodicity.from_value(value) is expected


def test_check_off_appends_and_keeps_sorted():
    habit = Habit("Water", "daily")
    habit.check_off(datetime(2026, 1, 2))
    habit.check_off(datetime(2026, 1, 1))
    assert habit.completion_dates == [datetime(2026, 1, 1), datetime(2026, 1, 2)]
    assert habit.last_completed == datetime(2026, 1, 2)


def test_check_off_defaults_to_now():
    habit = Habit("Water", "daily")
    before = datetime.now()
    moment = habit.check_off()
    assert moment >= before
    assert habit.last_completed == moment


def test_last_completed_is_none_when_empty():
    assert Habit("Water", "daily").last_completed is None


def test_initial_completion_dates_are_sorted():
    habit = Habit(
        "Water",
        "daily",
        completion_dates=[datetime(2026, 1, 3), datetime(2026, 1, 1)],
    )
    assert habit.completion_dates == [datetime(2026, 1, 1), datetime(2026, 1, 3)]


def test_update_changes_name_and_description():
    habit = Habit("Old", "daily", "old desc")
    habit.update(name="New", description="new desc")
    assert habit.name == "New"
    assert habit.description == "new desc"


def test_update_strips_and_validates_name():
    habit = Habit("Old", "daily")
    habit.update(name="  Renamed  ")
    assert habit.name == "Renamed"
    with pytest.raises(ValueError):
        habit.update(name="   ")


def test_update_partial_leaves_other_field_untouched():
    habit = Habit("Keep", "daily", "desc")
    habit.update(description="changed")
    assert habit.name == "Keep"
    assert habit.description == "changed"
