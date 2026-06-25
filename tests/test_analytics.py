"""Tests for the functional analytics module.

These cover the assignment's four required analyses plus the core streak/break
algorithm, including edge cases (empty, single, duplicate-in-period) and
year-boundary transitions for weekly and monthly habits.
"""

from datetime import datetime

from habit_tracker import analytics
from habit_tracker.habit import Habit, Periodicity


def test_get_all_habits_returns_names(sample_habits):
    assert analytics.get_all_habits(sample_habits) == [
        "Water",
        "Review",
        "Rent",
        "New",
    ]


def test_get_habits_by_periodicity(sample_habits):
    assert analytics.get_habits_by_periodicity(sample_habits, "daily") == [
        "Water",
        "New",
    ]
    assert analytics.get_habits_by_periodicity(
        sample_habits, Periodicity.WEEKLY
    ) == ["Review"]
    assert analytics.get_habits_by_periodicity(sample_habits, "monthly") == ["Rent"]


def test_longest_streak_daily():
    dates = [datetime(2026, 1, d) for d in (1, 2, 3, 5, 6)]
    assert analytics.longest_streak_for_completions(dates, Periodicity.DAILY) == 3


def test_longest_streak_weekly_across_year_boundary():
    dates = [
        datetime(2025, 12, 15),
        datetime(2025, 12, 22),
        datetime(2025, 12, 29),
        datetime(2026, 1, 5),
    ]
    assert analytics.longest_streak_for_completions(dates, Periodicity.WEEKLY) == 4


def test_longest_streak_monthly_across_year_boundary():
    dates = [
        datetime(2025, 11, 10),
        datetime(2025, 12, 5),
        datetime(2026, 1, 20),
        datetime(2026, 3, 3),
    ]
    assert analytics.longest_streak_for_completions(dates, Periodicity.MONTHLY) == 3


def test_streak_counts_same_period_once():
    dates = [datetime(2026, 1, 1, 8), datetime(2026, 1, 1, 20), datetime(2026, 1, 2, 9)]
    assert analytics.longest_streak_for_completions(dates, Periodicity.DAILY) == 2


def test_streak_empty_is_zero():
    assert analytics.longest_streak_for_completions([], Periodicity.DAILY) == 0


def test_streak_single_completion_is_one():
    assert (
        analytics.longest_streak_for_completions(
            [datetime(2026, 1, 1)], Periodicity.WEEKLY
        )
        == 1
    )


def test_calculate_longest_streak_across_all(sample_habits):
    assert analytics.calculate_longest_streak(sample_habits) == 3


def test_calculate_longest_streak_empty_list():
    assert analytics.calculate_longest_streak([]) == 0


def test_calculate_longest_streak_for_habit(sample_habits):
    assert analytics.calculate_longest_streak_for_habit(sample_habits, 1) == 3
    assert analytics.calculate_longest_streak_for_habit(sample_habits, 4) == 0
    assert analytics.calculate_longest_streak_for_habit(sample_habits, 999) == 0


def test_streaks_by_habit(sample_habits):
    assert analytics.streaks_by_habit(sample_habits) == [
        ("Water", 3),
        ("Review", 3),
        ("Rent", 3),
        ("New", 0),
    ]


def test_habit_with_longest_streak_returns_first_on_tie(sample_habits):
    assert analytics.habit_with_longest_streak(sample_habits) == ("Water", 3)


def test_habit_with_longest_streak_empty():
    assert analytics.habit_with_longest_streak([]) is None


def test_analytics_do_not_mutate_inputs(sample_habits):
    before = [list(h.completion_dates) for h in sample_habits]
    analytics.calculate_longest_streak(sample_habits)
    analytics.get_all_habits(sample_habits)
    analytics.streaks_by_habit(sample_habits)
    after = [list(h.completion_dates) for h in sample_habits]
    assert before == after


def test_struggle_score_counts_missed_daily():
    completions = [datetime(2026, 1, d) for d in (1, 2, 3, 4, 5, 6, 7)]
    assert analytics.struggle_score(
        completions, Periodicity.DAILY, datetime(2026, 1, 1), datetime(2026, 1, 10)
    ) == (3, 10)


def test_struggle_score_weekly_window():
    completions = [datetime(2026, 1, 5)]  # one completion in the first of three weeks
    assert analytics.struggle_score(
        completions, Periodicity.WEEKLY, datetime(2026, 1, 5), datetime(2026, 1, 19)
    ) == (2, 3)


def test_struggle_score_no_misses():
    completions = [datetime(2026, 1, d) for d in range(1, 11)]
    assert analytics.struggle_score(
        completions, Periodicity.DAILY, datetime(2026, 1, 1), datetime(2026, 1, 10)
    ) == (0, 10)


def test_most_struggled_ranks_worst_first():
    start, end = datetime(2026, 1, 1), datetime(2026, 1, 10)
    a = Habit("A", "daily", id=1, completion_dates=[datetime(2026, 1, 1), datetime(2026, 1, 2)])
    b = Habit("B", "daily", id=2, completion_dates=[datetime(2026, 1, d) for d in range(1, 10)])
    ranked = analytics.most_struggled_habits([a, b], start, end)
    assert [row[0] for row in ranked] == ["A", "B"]
    assert ranked[0] == ("A", 8, 10)


def test_most_struggled_empty():
    assert analytics.most_struggled_habits(
        [], datetime(2026, 1, 1), datetime(2026, 1, 10)
    ) == []
