"""Domain model for the habit tracker (object-oriented core).

This module defines the :class:`Periodicity` enumeration and the :class:`Habit`
class. Following the object-oriented paradigm, a :class:`Habit` is a
self-contained entity that owns its identifying data and the timestamps at
which its task was completed ("checked off").

Design note:
    Persistence is intentionally *not* handled here -- that is the job of
    :mod:`habit_tracker.database`. Likewise, streak calculations and other
    analytics are implemented as pure functions in
    :mod:`habit_tracker.analytics`. Keeping those concerns out of this class
    gives a clean separation between the object-oriented core (the state and
    behaviour of a habit) and the functional analytics layer, and lets the
    same ``Habit`` objects be reused by any future user interface (for example
    a web or desktop GUI) without modification.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum


class Periodicity(str, Enum):
    """How often a habit's task must be completed.

    The enum mixes in :class:`str` so that each member compares equal to and
    serialises as its plain text value (handy for SQLite storage), while code
    still benefits from validation against a fixed set of options.
    """

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_value(cls, value: str | Periodicity) -> Periodicity:
        """Coerce a string (or existing member) into a :class:`Periodicity`.

        Args:
            value: A periodicity name such as ``"daily"`` (case-insensitive)
                or an existing :class:`Periodicity` member.

        Returns:
            The matching :class:`Periodicity` member.

        Raises:
            ValueError: If ``value`` is not a recognised periodicity.
        """
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError as exc:
            valid = ", ".join(member.value for member in cls)
            raise ValueError(
                f"Invalid periodicity {value!r}. Expected one of: {valid}."
            ) from exc


class Habit:
    """A single habit: a task that must be completed once per period.

    Attributes:
        id: Database identifier, or ``None`` if the habit has not yet been
            persisted.
        name: Short task name, e.g. ``"Drink Water"``.
        description: Free-text description of the task.
        periodicity: The :class:`Periodicity` at which the task must be done.
        created_at: Timestamp at which the habit was created.
        completion_dates: Timestamps at which the task was checked off, always
            kept sorted in ascending order.
    """

    def __init__(
        self,
        name: str,
        periodicity: str | Periodicity,
        description: str = "",
        created_at: datetime | None = None,
        completion_dates: list[datetime] | None = None,
        id: int | None = None,
    ) -> None:
        """Create a habit, validating its name and periodicity.

        Args:
            name: Task name; must be non-empty.
            periodicity: ``"daily"``, ``"weekly"`` or ``"monthly"`` (or a
                :class:`Periodicity` member).
            description: Optional free-text description.
            created_at: Creation timestamp; defaults to now.
            completion_dates: Optional initial list of completion timestamps.
            id: Optional database id (set once persisted).

        Raises:
            ValueError: If ``name`` is empty or ``periodicity`` is invalid.
        """
        cleaned_name = (name or "").strip()
        if not cleaned_name:
            raise ValueError("Habit name must not be empty.")

        self.id = id
        self.name = cleaned_name
        self.description = (description or "").strip()
        self.periodicity = Periodicity.from_value(periodicity)
        self.created_at = created_at or datetime.now()
        self.completion_dates = sorted(completion_dates or [])

    def check_off(self, timestamp: datetime | None = None) -> datetime:
        """Record a completion of the task ("check it off").

        Args:
            timestamp: When the task was completed; defaults to now.

        Returns:
            The timestamp that was recorded.
        """
        moment = timestamp or datetime.now()
        self.completion_dates.append(moment)
        self.completion_dates.sort()
        return moment

    def update(
        self, name: str | None = None, description: str | None = None
    ) -> "Habit":
        """Update the habit's name and/or description in place, with validation.

        Only the arguments you pass are changed; passing ``None`` leaves that
        field untouched. (Periodicity and history are intentionally not
        editable here -- changing a habit's periodicity would invalidate its
        recorded streaks.)

        Args:
            name: New name; must be non-empty after stripping, if provided.
            description: New description (may be empty).

        Returns:
            The habit itself, to allow chaining.

        Raises:
            ValueError: If ``name`` is provided but blank.
        """
        if name is not None:
            cleaned = name.strip()
            if not cleaned:
                raise ValueError("Habit name must not be empty.")
            self.name = cleaned
        if description is not None:
            self.description = description.strip()
        return self

    @property
    def last_completed(self) -> datetime | None:
        """The most recent completion timestamp, or ``None`` if never done."""
        return self.completion_dates[-1] if self.completion_dates else None

    def __repr__(self) -> str:
        return (
            f"Habit(id={self.id!r}, name={self.name!r}, "
            f"periodicity={self.periodicity.value!r}, "
            f"completions={len(self.completion_dates)})"
        )
