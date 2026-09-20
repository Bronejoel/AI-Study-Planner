import sqlite3
from pathlib import Path
from datetime import date


DATABASE_PATH = Path(__file__).with_name("study_ai.db")


def get_connection(database_path=DATABASE_PATH):
    """Open and configure a connection to the SQLite database."""

    connection = sqlite3.connect(database_path)

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database(database_path=DATABASE_PATH):
    """Create the database tables when they do not already exist."""

    connection = get_connection(database_path)

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                difficulty INTEGER NOT NULL
                    CHECK (difficulty BETWEEN 1 AND 5),
                deadline TEXT NOT NULL,
                total_minutes INTEGER NOT NULL
                    CHECK (total_minutes > 0),
                remaining_minutes INTEGER NOT NULL
                    CHECK (remaining_minutes >= 0)
            )
            """
        )

        connection.commit()

    finally:
        connection.close()


#Create Subject 

def _validate_subject_details(name, difficulty, deadline, total_minutes):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Subject name cannot be empty.")
    if isinstance(difficulty, bool) or not isinstance(difficulty, int) or not 1 <= difficulty <= 5:
        raise ValueError("Difficulty must be a whole number between 1 and 5.")
    if type(deadline) is not date:
        raise ValueError("Deadline must be a Python date.")
    if isinstance(total_minutes, bool) or not isinstance(total_minutes, int) or total_minutes <= 0:
        raise ValueError("Total minutes must be a positive whole number.")
    return name.strip()


def invalidate_pending(connection):
    """Keep completed history, discard plans made with outdated inputs."""
    if connection.execute("SELECT 1 FROM sqlite_master WHERE name='study_sessions'").fetchone():
        connection.execute("DELETE FROM study_sessions WHERE completed_minutes = 0")
        connection.execute("UPDATE study_sessions SET minutes = completed_minutes")
        connection.execute("UPDATE planner_state SET needs_plan = 1 WHERE id = 1")


def create_subject(
    name,
    difficulty,
    deadline,
    total_minutes,
    database_path=DATABASE_PATH,
):
    """Save one subject and return its new database ID."""

    name = _validate_subject_details(name, difficulty, deadline, total_minutes)

    connection = get_connection(database_path)

    try:
        cursor = connection.execute(
            """
            INSERT INTO subjects (
                name,
                difficulty,
                deadline,
                total_minutes,
                remaining_minutes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                difficulty,
                deadline.isoformat(),
                total_minutes,
                total_minutes,
            ),
        )

        invalidate_pending(connection)
        connection.commit()

        return cursor.lastrowid

    finally:
        connection.close()

def _row_to_subject(row):
    """Convert a SQLite row into a planner subject dictionary."""

    if row is None:
        return None

    return {
        "id": row["id"],
        "name": row["name"],
        "difficulty": row["difficulty"],
        "deadline": date.fromisoformat(row["deadline"]),
        "total_minutes": row["total_minutes"],
        "remaining_minutes": row["remaining_minutes"],
    }

def get_subjects(database_path=DATABASE_PATH):
    """Return every saved subject ordered by its ID."""

    connection = get_connection(database_path)

    try:
        rows = connection.execute(
            """
            SELECT
                id,
                name,
                difficulty,
                deadline,
                total_minutes,
                remaining_minutes
            FROM subjects
            ORDER BY id
            """
        ).fetchall()

    finally:
        connection.close()

    return [
        _row_to_subject(row)
        for row in rows
    ]

def get_subject(subject_id, database_path=DATABASE_PATH):
    """Return one subject, or None when the ID does not exist."""

    connection = get_connection(database_path)

    try:
        row = connection.execute(
            """
            SELECT
                id,
                name,
                difficulty,
                deadline,
                total_minutes,
                remaining_minutes
            FROM subjects
            WHERE id = ?
            """,
            (subject_id,),
        ).fetchone()

    finally:
        connection.close()

    return _row_to_subject(row)


def update_subject(
    subject_id,
    name,
    difficulty,
    deadline,
    total_minutes,
    database_path=DATABASE_PATH,
):
    """Update a subject while preserving its completed progress."""

    name = _validate_subject_details(name, difficulty, deadline, total_minutes)

    connection = get_connection(database_path)

    try:
        connection.execute("BEGIN IMMEDIATE")
        current_subject = connection.execute(
            """
            SELECT total_minutes, remaining_minutes
            FROM subjects
            WHERE id = ?
            """,
            (subject_id,),
        ).fetchone()

        if current_subject is None:
            return False

        completed_minutes = (
            current_subject["total_minutes"]
            - current_subject["remaining_minutes"]
        )

        if total_minutes < completed_minutes:
            raise ValueError("Total workload cannot be less than already completed minutes.")
        new_remaining_minutes = total_minutes - completed_minutes

        cursor = connection.execute(
            """
            UPDATE subjects
            SET
                name = ?,
                difficulty = ?,
                deadline = ?,
                total_minutes = ?,
                remaining_minutes = ?
            WHERE id = ?
            """,
            (
                name,
                difficulty,
                deadline.isoformat(),
                total_minutes,
                new_remaining_minutes,
                subject_id,
            ),
        )

        invalidate_pending(connection)
        connection.commit()

        return cursor.rowcount == 1

    finally:
        connection.close()


def delete_subject(subject_id, database_path=DATABASE_PATH):
    """Delete one subject and return whether it existed."""

    connection = get_connection(database_path)

    try:
        cursor = connection.execute(
            """
            DELETE FROM subjects
            WHERE id = ?
            """,
            (subject_id,),
        )

        if cursor.rowcount:
            invalidate_pending(connection)
        connection.commit()

        return cursor.rowcount == 1

    finally:
        connection.close()
