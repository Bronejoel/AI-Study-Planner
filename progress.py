"""Transactional persistence for availability, plans and actual study progress."""
from contextlib import contextmanager
from datetime import date

from database import DATABASE_PATH, get_connection, initialize_database, invalidate_pending, _row_to_subject
from planner import generate_realistic_plan


@contextmanager
def transaction(database_path):
    connection = get_connection(database_path)
    try:
        # Serialize read-modify-write operations, including double clicks.
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_progress(database_path=DATABASE_PATH):
    """Add new tables without deleting existing Phase 3 subjects."""
    initialize_database(database_path)
    with transaction(database_path) as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS availability (
            study_date TEXT PRIMARY KEY,
            minutes INTEGER NOT NULL CHECK(minutes BETWEEN 0 AND 1440)
        )""")
        connection.execute("""CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            study_date TEXT NOT NULL,
            minutes INTEGER NOT NULL CHECK(minutes > 0),
            completed_minutes INTEGER NOT NULL DEFAULT 0
                CHECK(completed_minutes BETWEEN 0 AND minutes)
        )""")
        connection.execute("CREATE INDEX IF NOT EXISTS sessions_date ON study_sessions(study_date)")
        connection.execute("""CREATE TABLE IF NOT EXISTS planner_state (
            id INTEGER PRIMARY KEY CHECK(id = 1), needs_plan INTEGER NOT NULL DEFAULT 1
        )""")
        connection.execute("INSERT OR IGNORE INTO planner_state(id) VALUES (1)")


def save_availability(availability, database_path=DATABASE_PATH, today=None):
    today = today or date.today()
    if not availability:
        raise ValueError("Add at least one study date.")
    for day, minutes in availability.items():
        if type(day) is not date or day < today:
            raise ValueError("Study dates must be today or later.")
        if type(minutes) is not int or not 0 <= minutes <= 1440:
            raise ValueError("Available time must be between 0 and 24 hours per day.")
    with transaction(database_path) as connection:
        completed = dict(connection.execute(
            "SELECT study_date, SUM(completed_minutes) FROM study_sessions GROUP BY study_date"
        ).fetchall())
        for day, minutes in availability.items():
            if minutes < completed.get(day.isoformat(), 0):
                raise ValueError("Available hours cannot be less than time already completed on that date.")
        # Preserve past availability as history; replace only today's/future inputs.
        connection.execute("DELETE FROM availability WHERE study_date >= ?", (today.isoformat(),))
        connection.executemany("INSERT INTO availability VALUES (?, ?)",
                               [(day.isoformat(), minutes) for day, minutes in availability.items()])
        invalidate_pending(connection)


def regenerate_plan(database_path=DATABASE_PATH, today=None):
    today = today or date.today()
    with transaction(database_path) as connection:
        subjects = [_row_to_subject(row) for row in connection.execute("SELECT * FROM subjects ORDER BY id")]
        if not subjects:
            raise ValueError("Add at least one subject before generating a plan.")
        availability = {date.fromisoformat(row[0]): row[1] for row in connection.execute(
            "SELECT study_date, minutes FROM availability WHERE study_date >= ?", (today.isoformat(),)
        )}
        if not availability:
            raise ValueError("Save availability for today or a future date first.")
        completed = dict(connection.execute(
            "SELECT study_date, SUM(completed_minutes) FROM study_sessions GROUP BY study_date"
        ).fetchall())
        remaining_capacity = {day: max(0, minutes - completed.get(day.isoformat(), 0))
                              for day, minutes in availability.items()}
        plan = generate_realistic_plan(subjects, today, remaining_capacity)
        invalidate_pending(connection)
        # Compact one pending entry per subject/date, while retaining stable IDs
        # for previously completed history. Generating does NOT reduce workload.
        for day in plan["days"]:
            grouped = {}
            for session in day["sessions"]:
                sid = session["subject_id"]
                grouped[sid] = grouped.get(sid, 0) + session["minutes"]
            connection.executemany(
                "INSERT INTO study_sessions(subject_id, study_date, minutes) VALUES (?, ?, ?)",
                [(sid, day["date"].isoformat(), minutes) for sid, minutes in grouped.items()],
            )
        connection.execute("UPDATE planner_state SET needs_plan = 0 WHERE id = 1")


def record_completion(session_id, target_minutes, database_path=DATABASE_PATH, today=None):
    """Set an absolute completed amount; repeating the same request is harmless."""
    today = today or date.today()
    if type(target_minutes) is not int or target_minutes < 0:
        raise ValueError("Completed minutes must be a non-negative whole number.")
    with transaction(database_path) as connection:
        row = connection.execute("""SELECT s.*, p.remaining_minutes, p.total_minutes
            FROM study_sessions s JOIN subjects p ON p.id = s.subject_id WHERE s.id = ?""",
            (session_id,)).fetchone()
        if row is None:
            return False
        if target_minutes > row["minutes"]:
            raise ValueError("Completed time cannot exceed the scheduled time.")
        if target_minutes == row["completed_minutes"]:
            return True
        if date.fromisoformat(row["study_date"]) > today:
            raise ValueError("You can complete a session on its study date or later.")
        delta = target_minutes - row["completed_minutes"]
        remaining = row["remaining_minutes"] - delta
        if not 0 <= remaining <= row["total_minutes"]:
            raise ValueError("This change would exceed the subject's workload.")
        connection.execute("UPDATE subjects SET remaining_minutes = ? WHERE id = ?",
                           (remaining, row["subject_id"]))
        connection.execute("UPDATE study_sessions SET completed_minutes = ? WHERE id = ?",
                           (target_minutes, session_id))
        # A reversal can conflict with a regenerated pending plan. Clear pending
        # work and ask for regeneration; completed history remains intact.
        if delta < 0:
            invalidate_pending(connection)

    return True


def dashboard_data(database_path=DATABASE_PATH, today=None):
    today = today or date.today()
    connection = get_connection(database_path)
    try:
        subjects = [_row_to_subject(row) for row in connection.execute("SELECT * FROM subjects ORDER BY id")]
        availability = [{"date": row[0], "hours": row[1] / 60} for row in connection.execute(
            "SELECT study_date, minutes FROM availability WHERE study_date >= ? ORDER BY study_date",
            (today.isoformat(),))]
        sessions = [dict(row) for row in connection.execute("""SELECT s.*, p.name
            FROM study_sessions s JOIN subjects p ON s.subject_id = p.id
            ORDER BY s.study_date, s.id""")]
        needs_plan = bool(connection.execute("SELECT needs_plan FROM planner_state WHERE id=1").fetchone()[0])
    finally:
        connection.close()
    pending = {}
    days = {}
    for session in sessions:
        session["date"] = date.fromisoformat(session["study_date"])
        days.setdefault(session["date"], []).append(session)
        # Past pending work is missed work, not coverage of future workload.
        if session["date"] >= today:
            pending[session["subject_id"]] = pending.get(session["subject_id"], 0) + session["minutes"] - session["completed_minutes"]
    for subject in subjects:
        subject["completed_minutes"] = subject["total_minutes"] - subject["remaining_minutes"]
        subject["percent"] = round(subject["completed_minutes"] / subject["total_minutes"] * 100)
        subject["unscheduled_minutes"] = max(0, subject["remaining_minutes"] - pending.get(subject["id"], 0))
    return dict(subjects=subjects, availability_rows=availability, days=days,
                needs_plan=needs_plan, today=today,
                completed_total=sum(s["completed_minutes"] for s in subjects),
                remaining_total=sum(s["remaining_minutes"] for s in subjects))
