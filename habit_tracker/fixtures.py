"""Predefined habits and their sample tracking data ("test fixture").

The application ships with five predefined habits (two daily, two weekly and
one monthly) so that it is useful and analysable the moment it is first run,
and so that the test suite has realistic data to work with.

Each habit comes with a deterministic, hand-designed completion history that
spans the **six months ending 31 May 2026**. This window was chosen
deliberately: the assignment's 4-week minimum is far too short for a *monthly*
habit to build any streak at all, whereas six months lets the monthly habit
reach a six-period streak while the daily/weekly habits show a realistic mix of
long runs and breaks. (This is an intentional extension of the conception,
which originally proposed eight weeks.)

The patterns are fixed -- no randomness -- so the dataset, and every streak
computed from it, is fully reproducible.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from habit_tracker.database import DatabaseManager
from habit_tracker.habit import Habit, Periodicity

# Fixed window so the fixture is deterministic and reproducible.
START_DATE = datetime(2025, 12, 1)
NUM_DAYS = 182  # 1 Dec 2025 .. 31 May 2026 inclusive
NUM_WEEKS = 26
NUM_MONTHS = 6


def _first_monday_on_or_after(moment: datetime) -> datetime:
    """Return the first Monday falling on or after ``moment``."""
    return moment + timedelta(days=(7 - moment.weekday()) % 7)


def _add_months(moment: datetime, months: int) -> datetime:
    """Return ``moment`` shifted forward by a whole number of months."""
    total = (moment.year * 12 + moment.month - 1) + months
    year, month_index = divmod(total, 12)
    return moment.replace(year=year, month=month_index + 1)


def _daily_completions(skipped: set[int], hour: int = 8) -> list[datetime]:
    """Daily completions over the window, omitting the ``skipped`` day offsets."""
    return [
        (START_DATE + timedelta(days=offset)).replace(hour=hour)
        for offset in range(NUM_DAYS)
        if offset not in skipped
    ]


def _weekly_completions(
    skipped: set[int], weekday: int = 2, hour: int = 18
) -> list[datetime]:
    """Weekly completions (one per week) omitting the ``skipped`` week indices."""
    first_monday = _first_monday_on_or_after(START_DATE)
    return [
        (first_monday + timedelta(weeks=week, days=weekday)).replace(hour=hour)
        for week in range(NUM_WEEKS)
        if week not in skipped
    ]


def _monthly_completions(
    skipped: set[int] | None = None, day: int = 1, hour: int = 9
) -> list[datetime]:
    """Monthly completions (one per month) omitting the ``skipped`` indices."""
    skipped = skipped or set()
    base = START_DATE.replace(day=day, hour=hour)
    return [
        _add_months(base, index)
        for index in range(NUM_MONTHS)
        if index not in skipped
    ]


def predefined_habits() -> list[Habit]:
    """Build the five predefined habits with their sample completion histories.

    Returns:
        A list of unsaved :class:`Habit` objects (no database ids yet).
    """
    return [
        Habit(
            name="Drink Water",
            periodicity=Periodicity.DAILY,
            description="Drink at least 2 litres of water during the day.",
            created_at=START_DATE,
            # A few scattered misses -> a long ~11-week best run.
            completion_dates=_daily_completions(skipped={12, 13, 70, 71, 72, 150}),
        ),
        Habit(
            name="Morning Exercise",
            periodicity=Periodicity.DAILY,
            description="Do at least 30 minutes of physical activity.",
            created_at=START_DATE,
            # A weekly rest day plus a holiday gap -> short, realistic streaks.
            completion_dates=_daily_completions(
                skipped={off for off in range(NUM_DAYS) if off % 7 == 6}
                | set(range(90, 101))
            ),
        ),
        Habit(
            name="Weekly Review",
            periodicity=Periodicity.WEEKLY,
            description="Plan the week ahead and review the previous week.",
            created_at=START_DATE,
            completion_dates=_weekly_completions(skipped={3, 10, 11, 20}),
        ),
        Habit(
            name="Clean Apartment",
            periodicity=Periodicity.WEEKLY,
            description="Tidy and deep-clean the living space.",
            created_at=START_DATE,
            completion_dates=_weekly_completions(skipped={1}),
        ),
        Habit(
            name="Review Monthly Budget",
            periodicity=Periodicity.MONTHLY,
            description="Reconcile expenses and pay the recurring bills.",
            created_at=START_DATE,
            completion_dates=_monthly_completions(),
        ),
    ]


def seed_database(
    db: DatabaseManager, *, only_if_empty: bool = True
) -> list[Habit]:
    """Populate a database with the predefined habits.

    Args:
        db: The database to seed.
        only_if_empty: If ``True`` (default), seeding is skipped when the
            database already contains habits, so a user's own data is never
            overwritten.

    Returns:
        The habits now stored in the database (with their assigned ids).
    """
    if only_if_empty and db.count_habits() > 0:
        return db.get_all_habits()
    for habit in predefined_habits():
        db.add_habit(habit)
    return db.get_all_habits()
