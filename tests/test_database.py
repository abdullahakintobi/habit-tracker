"""Tests for the SQLite persistence layer (``DatabaseManager``)."""

from datetime import datetime

from habit_tracker.habit import Habit, Periodicity


def test_add_and_get_roundtrip(db):
    habit = Habit(
        "Water",
        "daily",
        "hydrate",
        completion_dates=[datetime(2026, 1, 1, 8), datetime(2026, 1, 2, 8)],
    )
    new_id = db.add_habit(habit)

    assert new_id == habit.id
    loaded = db.get_habit(new_id)
    assert loaded.name == "Water"
    assert loaded.description == "hydrate"
    assert loaded.periodicity is Periodicity.DAILY
    assert loaded.created_at == habit.created_at
    assert loaded.completion_dates == [
        datetime(2026, 1, 1, 8),
        datetime(2026, 1, 2, 8),
    ]


def test_get_missing_returns_none(db):
    assert db.get_habit(999) is None


def test_count_habits(db):
    assert db.count_habits() == 0
    db.add_habit(Habit("A", "daily"))
    db.add_habit(Habit("B", "weekly"))
    assert db.count_habits() == 2


def test_add_completion_persists(db):
    habit = Habit("Water", "daily")
    db.add_habit(habit)
    db.add_completion(habit.id, datetime(2026, 1, 1, 9))
    loaded = db.get_habit(habit.id)
    assert loaded.completion_dates == [datetime(2026, 1, 1, 9)]


def test_delete_habit_cascades_tracking(db):
    habit = Habit("Water", "daily", completion_dates=[datetime(2026, 1, 1)])
    db.add_habit(habit)
    assert db.delete_habit(habit.id) is True
    assert db.get_habit(habit.id) is None
    assert db.count_habits() == 0


def test_delete_missing_returns_false(db):
    assert db.delete_habit(123) is False


def test_get_all_habits_ordered_by_id(db):
    db.add_habit(Habit("A", "daily"))
    db.add_habit(Habit("B", "weekly"))
    db.add_habit(Habit("C", "monthly"))
    assert [h.name for h in db.get_all_habits()] == ["A", "B", "C"]


def test_persistence_survives_new_manager(db, tmp_path):
    """Data written by one manager is readable by another (true persistence)."""
    habit = Habit("Water", "daily", completion_dates=[datetime(2026, 1, 1)])
    db.add_habit(habit)

    from habit_tracker.database import DatabaseManager

    reopened = DatabaseManager(db.db_path)
    loaded = reopened.get_habit(habit.id)
    assert loaded is not None
    assert loaded.name == "Water"
    assert loaded.completion_dates == [datetime(2026, 1, 1)]


def test_update_habit_persists(db):
    habit = Habit("Old", "daily", "old")
    db.add_habit(habit)
    assert db.update_habit(habit.id, "New", "new desc") is True
    reloaded = db.get_habit(habit.id)
    assert reloaded.name == "New"
    assert reloaded.description == "new desc"


def test_update_missing_habit_returns_false(db):
    assert db.update_habit(999, "X", "Y") is False
