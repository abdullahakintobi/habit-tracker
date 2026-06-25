"""Analytics for the habit tracker, written in the functional paradigm.

Every function in this module is **pure**: it derives its result solely from
its arguments, never mutates the objects it is given, and produces no side
effects (no I/O, no database access, no global state). Results are computed by
composing small functions with ``map``, ``filter``, ``functools.reduce`` and
comprehensions. This is the deliberate counterpart to the object-oriented core
in :mod:`habit_tracker.habit`.

The four functions required by the assignment are:

* :func:`get_all_habits` -- list every currently tracked habit.
* :func:`get_habits_by_periodicity` -- list habits sharing a periodicity.
* :func:`calculate_longest_streak` -- longest streak across all habits.
* :func:`calculate_longest_streak_for_habit` -- longest streak for one habit.

A few extra helpers (:func:`longest_streak_for_completions`,
:func:`streaks_by_habit`, :func:`habit_with_longest_streak`) make the CLI output
richer and keep the streak algorithm independently testable.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from functools import reduce
from typing import Iterable

from habit_tracker.habit import Habit, Periodicity


def _period_index(moment: datetime, periodicity: Periodicity) -> int:
    """Map a timestamp to the integer index of the period it falls in.

    Consecutive periods map to consecutive integers, which turns
    "consecutive-period" streak detection into a simple search for runs of
    consecutive integers.

    * Daily   -> the date's proleptic Gregorian ordinal (consecutive days
      differ by 1).
    * Weekly  -> the ordinal of that week's Monday divided by 7 (consecutive
      ISO weeks differ by 1, including across year boundaries).
    * Monthly -> ``year * 12 + month`` (consecutive months differ by 1,
      including across year boundaries).
    """
    if periodicity == Periodicity.DAILY:
        return moment.toordinal()
    if periodicity == Periodicity.WEEKLY:
        monday = moment - timedelta(days=moment.weekday())
        return monday.toordinal() // 7
    return moment.year * 12 + (moment.month - 1)


def longest_streak_for_completions(
    completions: Iterable[datetime], periodicity: Periodicity
) -> int:
    """Return the longest run of consecutive periods that were completed.

    Multiple completions in the same period count once; a gap of more than one
    period "breaks" the streak. With no completions the streak is ``0``.

    Args:
        completions: Timestamps at which the task was checked off.
        periodicity: The habit's periodicity, defining what "consecutive" means.

    Returns:
        The length of the longest streak, in periods.
    """
    indices = sorted({_period_index(moment, periodicity) for moment in completions})
    if not indices:
        return 0

    def advance(state: tuple[int | None, int, int], index: int) -> tuple[int, int, int]:
        previous, current_run, best = state
        current_run = current_run + 1 if previous is not None and index == previous + 1 else 1
        return index, current_run, max(best, current_run)

    _, _, best = reduce(advance, indices, (None, 0, 0))
    return best


def _streak_of(habit: Habit) -> int:
    """Longest streak for a single habit (convenience wrapper)."""
    return longest_streak_for_completions(habit.completion_dates, habit.periodicity)


def get_all_habits(habits: Iterable[Habit]) -> list[str]:
    """Return the names of all currently tracked habits.

    Args:
        habits: The habits to list.

    Returns:
        A list of habit names, in the order given.
    """
    return [habit.name for habit in habits]


def get_habits_by_periodicity(
    habits: Iterable[Habit], periodicity: str | Periodicity
) -> list[str]:
    """Return the names of habits that share the given periodicity.

    Args:
        habits: The habits to filter.
        periodicity: ``"daily"``, ``"weekly"`` or ``"monthly"`` (or a
            :class:`Periodicity` member).

    Returns:
        Names of the matching habits.
    """
    target = Periodicity.from_value(periodicity)
    matching = filter(lambda habit: habit.periodicity == target, habits)
    return list(map(lambda habit: habit.name, matching))


def calculate_longest_streak(habits: Iterable[Habit]) -> int:
    """Return the longest run streak across all given habits.

    Args:
        habits: The habits to consider.

    Returns:
        The single longest streak among them, or ``0`` if there are none.
    """
    return max(map(_streak_of, habits), default=0)


def calculate_longest_streak_for_habit(
    habits: Iterable[Habit], habit_id: int
) -> int:
    """Return the longest run streak for one habit, identified by id.

    Args:
        habits: The habits to search.
        habit_id: The database id of the habit of interest.

    Returns:
        The habit's longest streak, or ``0`` if it is not found or has no
        completions.
    """
    habit = next((h for h in habits if h.id == habit_id), None)
    return _streak_of(habit) if habit is not None else 0


def streaks_by_habit(habits: Iterable[Habit]) -> list[tuple[str, int]]:
    """Return ``(habit name, longest streak)`` pairs for every habit."""
    return [(habit.name, _streak_of(habit)) for habit in habits]


def habit_with_longest_streak(
    habits: Iterable[Habit],
) -> tuple[str, int] | None:
    """Return the ``(name, streak)`` of the record-holding habit.

    Returns:
        The habit with the longest streak as a ``(name, streak)`` pair, or
        ``None`` if there are no habits.
    """
    return max(streaks_by_habit(habits), key=lambda pair: pair[1], default=None)


def _expected_periods(start: datetime, end: datetime, periodicity: Periodicity) -> int:
    """How many whole periods the inclusive window ``[start, end]`` spans (0 if end < start)."""
    span = _period_index(end, periodicity) - _period_index(start, periodicity) + 1
    return max(span, 0)


def struggle_score(
    completions: Iterable[datetime],
    periodicity: Periodicity,
    start: datetime,
    end: datetime,
) -> tuple[int, int]:
    """Return ``(missed, expected)`` periods for one habit within ``[start, end]``.

    ``expected`` is the number of periods the window spans; ``missed`` is how
    many of those periods had no completion. A higher ``missed / expected``
    ratio means the user struggled more with the habit in that window.

    Args:
        completions: The habit's completion timestamps.
        periodicity: The habit's periodicity.
        start: Inclusive start of the window.
        end: Inclusive end of the window.

    Returns:
        A ``(missed, expected)`` pair.
    """
    expected = _expected_periods(start, end, periodicity)
    completed = len(
        {_period_index(c, periodicity) for c in completions if start <= c <= end}
    )
    return max(expected - completed, 0), expected


def most_struggled_habits(
    habits: Iterable[Habit], start: datetime, end: datetime
) -> list[tuple[str, int, int]]:
    """Rank habits by how much the user struggled with them in ``[start, end]``.

    This answers the brief's example question "with which habits did I struggle
    most last month?". Habits are ranked by their miss ratio (then by absolute
    misses as a tie-breaker), most-struggled first.

    Args:
        habits: The habits to rank.
        start: Inclusive start of the window.
        end: Inclusive end of the window.

    Returns:
        A list of ``(name, missed, expected)`` triples, most-struggled first.
    """
    rows = [
        (habit.name, *struggle_score(habit.completion_dates, habit.periodicity, start, end))
        for habit in habits
    ]
    return sorted(rows, key=lambda r: (r[1] / r[2] if r[2] else 0.0, r[1]), reverse=True)
