"""Shared pytest fixtures (dummy data) for the habit-tracker test suite.

Small, hand-crafted datasets with *known* answers are defined here so the tests
can assert exact streak values rather than re-deriving them. This is the
"dummy data to assist with testing" recommended in the tutor feedback.
"""

from datetime import datetime

import pytest

from habit_tracker.database import DatabaseManager
from habit_tracker.habit import Habit


@pytest.fixture
def db(tmp_path):
    """A DatabaseManager backed by a throwaway on-disk SQLite file."""
    return DatabaseManager(str(tmp_path / "test.db"))


@pytest.fixture
def sample_habits():
    """Four habits with deliberately known longest streaks.

    * Water (daily):   1,2,3 then 5,6           -> longest 3
    * Review (weekly): three consecutive weeks   -> longest 3
    * Rent (monthly):  Nov,Dec,Jan then Mar      -> longest 3
    * New (daily):     no completions            -> longest 0
    """
    water = Habit(
        "Water",
        "daily",
        id=1,
        completion_dates=[datetime(2026, 1, d) for d in (1, 2, 3, 5, 6)],
    )
    review = Habit(
        "Review",
        "weekly",
        id=2,
        completion_dates=[
            datetime(2026, 1, 5),
            datetime(2026, 1, 12),
            datetime(2026, 1, 19),
        ],
    )
    rent = Habit(
        "Rent",
        "monthly",
        id=3,
        completion_dates=[
            datetime(2025, 11, 1),
            datetime(2025, 12, 1),
            datetime(2026, 1, 1),
            datetime(2026, 3, 1),
        ],
    )
    new = Habit("New", "daily", id=4, completion_dates=[])
    return [water, review, rent, new]
