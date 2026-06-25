"""SQLite persistence layer for the habit tracker.

``DatabaseManager`` is the single place that knows how habits and their
completion events are stored on disk. Keeping all SQL in one module (rather
than inside the :class:`~habit_tracker.habit.Habit` class) follows the
separation-of-concerns principle requested in the tutor feedback: the domain
object stays storage-agnostic and the analytics layer stays side-effect free.

Storage model -- two normalised tables:

* ``habits``   -- one row per habit (id, name, description, periodicity,
  created_at).
* ``tracking`` -- one row per check-off (habit_id, check_off_date), linked to
  ``habits`` with an ``ON DELETE CASCADE`` foreign key so deleting a habit also
  removes its history.

Timestamps are stored as ISO-8601 strings and parsed back into
:class:`datetime.datetime` objects on load.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime

from habit_tracker.habit import Habit

DEFAULT_DB_PATH = "habits.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS habits (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    periodicity TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tracking (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id       INTEGER NOT NULL,
    check_off_date TEXT NOT NULL,
    FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE
);
"""


class DatabaseManager:
    """Reads and writes habits and their completion history to SQLite.

    A short-lived connection is opened per operation, which keeps the class
    simple and avoids stale-connection issues. Because each call opens its own
    connection, an on-disk database path should be used (the default,
    ``"habits.db"``); ``":memory:"`` would not persist between calls.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        """Open/locate the database file and ensure the schema exists.

        Args:
            db_path: Path to the SQLite file. Created automatically if absent.
        """
        self.db_path = str(db_path)
        self.setup()

    def _connect(self) -> sqlite3.Connection:
        """Return a new connection with row access by name and FKs enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def setup(self) -> None:
        """Create the ``habits`` and ``tracking`` tables if they do not exist."""
        with closing(self._connect()) as conn, conn:
            conn.executescript(_SCHEMA)

    # -- Writes ----------------------------------------------------------

    def add_habit(self, habit: Habit) -> int:
        """Persist a new habit (and any completion dates it already holds).

        The habit's ``id`` attribute is updated in place with the new row id.

        Args:
            habit: The habit to store.

        Returns:
            The database id assigned to the habit.
        """
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                "INSERT INTO habits (name, description, periodicity, created_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    habit.name,
                    habit.description,
                    habit.periodicity.value,
                    habit.created_at.isoformat(),
                ),
            )
            habit.id = int(cursor.lastrowid)
            if habit.completion_dates:
                conn.executemany(
                    "INSERT INTO tracking (habit_id, check_off_date) VALUES (?, ?)",
                    [(habit.id, dt.isoformat()) for dt in habit.completion_dates],
                )
        return habit.id

    def delete_habit(self, habit_id: int) -> bool:
        """Delete a habit and (via cascade) all of its tracking rows.

        Args:
            habit_id: Id of the habit to remove.

        Returns:
            ``True`` if a habit was deleted, ``False`` if no such id existed.
        """
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
            return cursor.rowcount > 0

    def update_habit(self, habit_id: int, name: str, description: str) -> bool:
        """Update a habit's name and description.

        Args:
            habit_id: Id of the habit to update.
            name: New name.
            description: New description.

        Returns:
            ``True`` if a habit was updated, ``False`` if no such id existed.
        """
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                "UPDATE habits SET name = ?, description = ? WHERE id = ?",
                (name, description, habit_id),
            )
            return cursor.rowcount > 0

    def add_completion(
        self, habit_id: int, timestamp: datetime | None = None
    ) -> datetime:
        """Record a check-off for a habit.

        Args:
            habit_id: Id of the habit being checked off.
            timestamp: When it was completed; defaults to now.

        Returns:
            The timestamp that was stored.
        """
        moment = timestamp or datetime.now()
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO tracking (habit_id, check_off_date) VALUES (?, ?)",
                (habit_id, moment.isoformat()),
            )
        return moment

    # -- Reads -----------------------------------------------------------

    def get_all_habits(self) -> list[Habit]:
        """Load every habit together with its completion history.

        Returns:
            A list of :class:`Habit` objects ordered by id.
        """
        with closing(self._connect()) as conn:
            habit_rows = conn.execute(
                "SELECT id, name, description, periodicity, created_at "
                "FROM habits ORDER BY id"
            ).fetchall()
            tracking_rows = conn.execute(
                "SELECT habit_id, check_off_date FROM tracking"
            ).fetchall()

        completions: dict[int, list[datetime]] = {}
        for row in tracking_rows:
            completions.setdefault(row["habit_id"], []).append(
                datetime.fromisoformat(row["check_off_date"])
            )
        return [
            self._row_to_habit(row, completions.get(row["id"], []))
            for row in habit_rows
        ]

    def get_habit(self, habit_id: int) -> Habit | None:
        """Load a single habit by id, or ``None`` if it does not exist."""
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT id, name, description, periodicity, created_at "
                "FROM habits WHERE id = ?",
                (habit_id,),
            ).fetchone()
            if row is None:
                return None
            tracking_rows = conn.execute(
                "SELECT check_off_date FROM tracking WHERE habit_id = ? "
                "ORDER BY check_off_date",
                (habit_id,),
            ).fetchall()
        completions = [
            datetime.fromisoformat(t["check_off_date"]) for t in tracking_rows
        ]
        return self._row_to_habit(row, completions)

    def count_habits(self) -> int:
        """Return the number of stored habits (useful for seeding logic)."""
        with closing(self._connect()) as conn:
            return int(conn.execute("SELECT COUNT(*) FROM habits").fetchone()[0])

    @staticmethod
    def _row_to_habit(row: sqlite3.Row, completion_dates: list[datetime]) -> Habit:
        """Rebuild a :class:`Habit` from a database row and its completions."""
        return Habit(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            periodicity=row["periodicity"],
            created_at=datetime.fromisoformat(row["created_at"]),
            completion_dates=completion_dates,
        )
