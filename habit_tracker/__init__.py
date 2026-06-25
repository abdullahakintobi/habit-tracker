"""Habit Tracker backend.

A small, dependency-light habit-tracking backend built for the IU course
"Object Oriented and Functional Programming with Python" (DLBDSOOFPP01).

The package is split into focused modules so that each concern lives on its
own (see the tutor's maintainability feedback):

* :mod:`habit_tracker.habit`     -- the object-oriented core (``Habit`` class).
* :mod:`habit_tracker.database`  -- SQLite persistence (``DatabaseManager``).
* :mod:`habit_tracker.analytics` -- pure functional-programming analytics.
* :mod:`habit_tracker.fixtures`  -- predefined habits and sample tracking data.
* :mod:`habit_tracker.cli`       -- the interactive command-line interface.
"""

from habit_tracker.habit import Habit, Periodicity

__all__ = ["Habit", "Periodicity"]
__version__ = "1.0.0"
