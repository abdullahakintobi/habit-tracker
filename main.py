"""Command-line entry point for the habit tracker.

Usage:
    python main.py

On first launch the application creates a local SQLite database
(``habits.db``) and seeds it with five predefined habits and ~6 months of
sample tracking data.
"""

from habit_tracker.cli import run

if __name__ == "__main__":
    run()
