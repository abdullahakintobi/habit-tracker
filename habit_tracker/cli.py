"""Interactive command-line interface, built with the ``click`` library.

This is the thin presentation layer that the user interacts with. It owns no
business logic of its own: it reads and writes habits through
:class:`~habit_tracker.database.DatabaseManager` and answers analytical
questions through the pure functions in :mod:`habit_tracker.analytics`. Because
all of the logic lives behind those two seams, the same backend could later be
driven by a different front end (a web or desktop GUI) without any change to
the core -- which directly answers the tutor's question about future user
interaction tools.

The menu mirrors the activity diagram from the conception: a main loop offering
*manage* (list/create/delete), *check off*, and *analyse* branches.
"""

from __future__ import annotations

from datetime import datetime, timedelta

# Importing readline (when available) gives every click.prompt full line editing
# -- Left/Right arrows, Home/End and history -- instead of raw ^[[D / ^[[C escape
# sequences appearing in the terminal. The import alone installs the input() hook.
try:  # pragma: no cover - availability depends on the platform
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - e.g. some Windows setups
    readline = None

import click

from habit_tracker import analytics, fixtures
from habit_tracker.database import DEFAULT_DB_PATH, DatabaseManager
from habit_tracker.habit import Habit, Periodicity

_PERIODICITY_BY_NUMBER = {
    "1": Periodicity.DAILY,
    "2": Periodicity.WEEKLY,
    "3": Periodicity.MONTHLY,
}


def _period_unit(periodicity: Periodicity, count: int) -> str:
    """Return a human label for a streak length, e.g. ``"days"``/``"week"``."""
    singular = {"daily": "day", "weekly": "week", "monthly": "month"}[
        periodicity.value
    ]
    return singular if count == 1 else singular + "s"


def _format_dt(moment: datetime) -> str:
    """Format a completion timestamp as e.g. ``2026-06-08 at 17:20`` (24-hour)."""
    return moment.strftime("%Y-%m-%d at %H:%M")


def _prompt_periodicity() -> Periodicity:
    """Prompt for a periodicity by number (1 = daily, 2 = weekly, 3 = monthly)."""
    click.echo("  1. Daily    2. Weekly    3. Monthly")
    choice = click.prompt(
        "Periodicity", type=click.Choice(["1", "2", "3"]), show_choices=False
    )
    return _PERIODICITY_BY_NUMBER[choice]


def _print_menu() -> None:
    """Print the main menu."""
    click.secho("\n========== Habit Tracker ==========", fg="cyan", bold=True)
    click.echo("  1. List habits")
    click.echo("  2. Create a habit")
    click.echo("  3. Edit a habit")
    click.echo("  4. Delete a habit")
    click.echo("  5. Check off a task")
    click.echo("  6. Analyse progress")
    click.echo("  0. Exit")


def _select_habit(db: DatabaseManager, verb: str) -> Habit | None:
    """Show the habits and prompt the user to pick one by id.

    Args:
        db: The database to read from.
        verb: What the selection is for (used in the prompt text).

    Returns:
        The chosen :class:`Habit`, or ``None`` if there are none or the id is
        invalid.
    """
    habits = db.get_all_habits()
    if not habits:
        click.secho("No habits available yet.", fg="yellow")
        return None
    click.echo(f"\nSelect a habit to {verb}:")
    for habit in habits:
        click.echo(f"  [{habit.id}] {habit.name} ({habit.periodicity.value})")
    habit_id = click.prompt("Habit id", type=int)
    habit = db.get_habit(habit_id)
    if habit is None:
        click.secho(f"No habit found with id {habit_id}.", fg="red")
    return habit


def _prompt_completion_datetime() -> datetime:
    """Prompt for a completion date (and optional time), defaulting to now.

    Accepts ``YYYY-MM-DD HH:MM`` (24-hour) or ``YYYY-MM-DD`` (time defaults to
    00:00). A blank entry records the current date and time.
    """
    while True:
        raw = click.prompt(
            "Completion date/time (YYYY-MM-DD [HH:MM], blank = now)",
            default="",
            show_default=False,
        ).strip()
        if not raw:
            return datetime.now()
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        click.secho("Please use YYYY-MM-DD or YYYY-MM-DD HH:MM (24-hour).", fg="red")


def _list_habits(db: DatabaseManager) -> None:
    """Print every habit with its periodicity, count and last check-off."""
    habits = db.get_all_habits()
    if not habits:
        click.secho("No habits yet. Create one from the menu.", fg="yellow")
        return
    click.secho("\nYour habits:", fg="green", bold=True)
    for habit in habits:
        last = (
            _format_dt(habit.last_completed)
            if habit.last_completed
            else "never"
        )
        click.echo(
            f"  [{habit.id}] {habit.name} - {habit.periodicity.value}, "
            f"{len(habit.completion_dates)} check-offs, last: {last}"
        )
        if habit.description:
            click.echo(f"        {habit.description}")


def _create_habit(db: DatabaseManager) -> None:
    """Prompt for habit details and store the new habit."""
    name = click.prompt("Habit name").strip()
    description = click.prompt(
        "Description (optional)", default="", show_default=False
    ).strip()
    periodicity = _prompt_periodicity()
    try:
        habit = Habit(name=name, periodicity=periodicity, description=description)
    except ValueError as error:
        click.secho(f"Could not create habit: {error}", fg="red")
        return
    db.add_habit(habit)
    click.secho(f"Created '{habit.name}' (id {habit.id}).", fg="green")


def _edit_habit(db: DatabaseManager) -> None:
    """Select a habit and edit its name and/or description.

    Pressing Enter at a prompt keeps the current value. Periodicity is not
    editable, since changing it would invalidate the recorded streaks.
    """
    habit = _select_habit(db, "edit")
    if habit is None:
        return
    new_name = click.prompt("New name", default=habit.name)
    new_description = click.prompt(
        "New description",
        default=habit.description,
        show_default=bool(habit.description),
    )
    try:
        habit.update(name=new_name, description=new_description)
    except ValueError as error:
        click.secho(f"Could not update habit: {error}", fg="red")
        return
    db.update_habit(habit.id, habit.name, habit.description)
    click.secho(f"Updated '{habit.name}' (id {habit.id}).", fg="green")


def _delete_habit(db: DatabaseManager) -> None:
    """Select a habit and delete it (with confirmation)."""
    habit = _select_habit(db, "delete")
    if habit is None:
        return
    if click.confirm(f"Delete '{habit.name}' and all of its history?"):
        db.delete_habit(habit.id)
        click.secho(f"Deleted '{habit.name}'.", fg="green")
    else:
        click.echo("Cancelled.")


def _check_off(db: DatabaseManager) -> None:
    """Select a habit and record a completion for it."""
    habit = _select_habit(db, "check off")
    if habit is None:
        return
    moment = _prompt_completion_datetime()
    db.add_completion(habit.id, moment)
    click.secho(
        f"Checked off '{habit.name}' on {_format_dt(moment)}.", fg="green"
    )


def _analyse(db: DatabaseManager) -> None:
    """Sub-menu exposing the functional analytics."""
    if not db.get_all_habits():
        click.secho("No habits to analyse yet.", fg="yellow")
        return
    while True:
        click.secho("\n-- Analyse progress --", fg="blue", bold=True)
        click.echo("  1. List all tracked habits")
        click.echo("  2. List habits by periodicity")
        click.echo("  3. Longest streak (all habits)")
        click.echo("  4. Longest streak for a specific habit")
        click.echo("  5. Longest streak per habit (overview)")
        click.echo("  6. Habits struggled with most (last 30 days)")
        click.echo("  0. Back")
        choice = click.prompt(
            "Select", type=click.Choice(["0", "1", "2", "3", "4", "5", "6"]),
            show_choices=False,
        )
        if choice == "0":
            return

        habits = db.get_all_habits()
        if choice == "1":
            click.echo("Tracked habits: " + ", ".join(analytics.get_all_habits(habits)))
        elif choice == "2":
            period = _prompt_periodicity()
            names = analytics.get_habits_by_periodicity(habits, period)
            click.echo(
                f"{period.value} habits: "
                + (", ".join(names) if names else "(none)")
            )
        elif choice == "3":
            holder = max(
                habits,
                key=lambda h: analytics.calculate_longest_streak_for_habit(habits, h.id),
            )
            value = analytics.calculate_longest_streak(habits)
            unit = _period_unit(holder.periodicity, value)
            click.secho(
                f"Longest streak overall: {value} {unit} ({holder.name}).",
                fg="green",
            )
        elif choice == "4":
            habit = _select_habit(db, "analyse")
            if habit is not None:
                value = analytics.calculate_longest_streak_for_habit(habits, habit.id)
                unit = _period_unit(habit.periodicity, value)
                click.secho(f"'{habit.name}' longest streak: {value} {unit}.", fg="green")
        elif choice == "5":
            click.secho("Longest streak per habit:", fg="green")
            for name, value in analytics.streaks_by_habit(habits):
                click.echo(f"  {name}: {value}")
        elif choice == "6":
            now = datetime.now()
            ranked = analytics.most_struggled_habits(habits, now - timedelta(days=30), now)
            click.secho("Habits you struggled with most (last 30 days):", fg="green")
            for name, missed, expected in ranked:
                click.echo(f"  {name}: missed {missed} of {expected} periods")


def run(db_path: str = DEFAULT_DB_PATH) -> None:
    """Start the interactive habit-tracker session.

    On first run (empty database) the five predefined habits and their sample
    tracking data are seeded automatically.

    Args:
        db_path: Path to the SQLite database file to use.
    """
    db = DatabaseManager(db_path)
    was_empty = db.count_habits() == 0
    fixtures.seed_database(db)
    if was_empty:
        click.secho(
            f"Welcome! Initialised with {db.count_habits()} predefined habits "
            "and ~6 months of sample data.",
            fg="cyan",
        )

    actions = {
        "1": _list_habits,
        "2": _create_habit,
        "3": _edit_habit,
        "4": _delete_habit,
        "5": _check_off,
        "6": _analyse,
    }
    while True:
        _print_menu()
        try:
            choice = click.prompt(
                "Select an option",
                type=click.Choice(list(actions) + ["0"]),
                show_choices=False,
            )
        except (EOFError, click.exceptions.Abort):
            click.echo()
            choice = "0"

        if choice == "0":
            click.secho("Goodbye!", fg="cyan")
            return
        try:
            actions[choice](db)
        except (EOFError, click.exceptions.Abort):
            click.echo("\n(cancelled)")
