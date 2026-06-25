"""Tests for the command-line interface handlers (habit_tracker.cli).

The interactive prompts are driven by monkeypatching ``click.prompt`` /
``click.confirm`` with scripted answers, so the handlers can be exercised
deterministically without real keyboard input.
"""

from datetime import datetime

import click

from habit_tracker import cli
from habit_tracker.database import DatabaseManager
from habit_tracker.habit import Habit, Periodicity


def _script(monkeypatch, values):
    """Feed scripted return values to successive ``click.prompt`` calls."""
    answers = iter(values)
    monkeypatch.setattr(click, "prompt", lambda *a, **k: next(answers))


def test_create_habit_via_cli(db, monkeypatch):
    _script(monkeypatch, ["Meditate", "Be calm", "1"])  # 1 = daily
    cli._create_habit(db)
    assert [h.name for h in db.get_all_habits()] == ["Meditate"]


def test_create_habit_rejects_empty_name(db, monkeypatch, capsys):
    _script(monkeypatch, ["", "", "1"])  # blank name, then 1 = daily
    cli._create_habit(db)
    assert "Could not create habit" in capsys.readouterr().out
    assert db.count_habits() == 0


def test_check_off_via_cli(db, monkeypatch):
    habit = Habit("Read", "daily")
    db.add_habit(habit)
    _script(monkeypatch, [habit.id, ""])  # habit id, then blank date -> now
    cli._check_off(db)
    assert len(db.get_habit(habit.id).completion_dates) == 1


def test_delete_habit_via_cli(db, monkeypatch):
    habit = Habit("Temp", "daily")
    db.add_habit(habit)
    _script(monkeypatch, [habit.id])
    monkeypatch.setattr(click, "confirm", lambda *a, **k: True)
    cli._delete_habit(db)
    assert db.get_habit(habit.id) is None


def test_full_session_seeds_and_creates(tmp_path, monkeypatch, capsys):
    """Drive the whole interactive loop: seed -> create a habit -> exit."""
    db_path = str(tmp_path / "cli.db")
    _script(monkeypatch, ["2", "Meditate", "Be calm", "1", "0"])  # 1 = daily
    cli.run(db_path)
    out = capsys.readouterr().out
    assert "Created 'Meditate'" in out
    assert "Goodbye!" in out
    names = [h.name for h in DatabaseManager(db_path).get_all_habits()]
    assert "Meditate" in names
    assert len(names) == 6  # 5 predefined + the one created here


def test_edit_habit_via_cli(db, monkeypatch):
    habit = Habit("Old", "daily", "old")
    db.add_habit(habit)
    _script(monkeypatch, [habit.id, "Renamed", "new desc"])
    cli._edit_habit(db)
    reloaded = db.get_habit(habit.id)
    assert reloaded.name == "Renamed"
    assert reloaded.description == "new desc"


def test_check_off_records_time(db, monkeypatch):
    habit = Habit("Read", "daily")
    db.add_habit(habit)
    _script(monkeypatch, [habit.id, "2026-06-08 17:20"])
    cli._check_off(db)
    stamp = db.get_habit(habit.id).completion_dates[0]
    assert (stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute) == (
        2026, 6, 8, 17, 20,
    )


def test_list_shows_completion_time(db, monkeypatch, capsys):
    habit = Habit("Read", "daily", completion_dates=[datetime(2026, 6, 8, 17, 20)])
    db.add_habit(habit)
    cli._list_habits(db)
    assert "2026-06-08 at 17:20" in capsys.readouterr().out


def test_prompt_periodicity_maps_numbers(monkeypatch):
    _script(monkeypatch, ["2"])
    assert cli._prompt_periodicity() is Periodicity.WEEKLY
