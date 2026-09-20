from datetime import date

from database import (
    create_subject,
    delete_subject,
    get_connection,
    get_subject,
    get_subjects,
    initialize_database,
    update_subject,
)
def save_python_subject(database_path):
    """Create a reusable Python subject for database tests."""

    return create_subject(
        name="Python",
        difficulty=4,
        deadline=date(2026, 9, 20),
        total_minutes=180,
        database_path=database_path,
    )

def test_create_subject_saves_subject(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    subject_id = create_subject(
        name="Python",
        difficulty=4,
        deadline=date(2026, 9, 20),
        total_minutes=180,
        database_path=database_path,
    )

    connection = get_connection(database_path)

    try:
        subject = connection.execute(
            """
            SELECT *
            FROM subjects
            WHERE id = ?
            """,
            (subject_id,),
        ).fetchone()

    finally:
        connection.close()

    assert subject is not None
    assert subject["id"] == subject_id
    assert subject["name"] == "Python"
    assert subject["difficulty"] == 4
    assert subject["deadline"] == "2026-09-20"
    assert subject["total_minutes"] == 180
    assert subject["remaining_minutes"] == 180


def test_create_subject_returns_different_ids(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    first_id = create_subject(
        name="Python",
        difficulty=4,
        deadline=date(2026, 9, 20),
        total_minutes=180,
        database_path=database_path,
    )

    second_id = create_subject(
        name="Mathematics",
        difficulty=5,
        deadline=date(2026, 9, 18),
        total_minutes=240,
        database_path=database_path,
    )

    assert first_id == 1
    assert second_id == 2

def test_initialize_database_creates_database_file(tmp_path):
    database_path = tmp_path / "test.db"

    initialize_database(database_path)

    assert database_path.exists()


def test_initialize_database_creates_subjects_table(tmp_path):
    database_path = tmp_path / "test.db"

    initialize_database(database_path)

    connection = get_connection(database_path)

    try:
        table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'subjects'
            """
        ).fetchone()

    finally:
        connection.close()

    assert table is not None
    assert table["name"] == "subjects"


def test_subjects_table_contains_expected_columns(tmp_path):
    database_path = tmp_path / "test.db"

    initialize_database(database_path)

    connection = get_connection(database_path)

    try:
        rows = connection.execute(
            "PRAGMA table_info(subjects)"
        ).fetchall()

    finally:
        connection.close()

    column_names = {
        row["name"]
        for row in rows
    }

    assert column_names == {
        "id",
        "name",
        "difficulty",
        "deadline",
        "total_minutes",
        "remaining_minutes",
    }


def test_database_can_be_initialized_multiple_times(tmp_path):
    database_path = tmp_path / "test.db"

    initialize_database(database_path)
    initialize_database(database_path)

    assert database_path.exists()


def test_get_subjects_returns_empty_list_when_database_is_empty(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    subjects = get_subjects(database_path)

    assert subjects == []


def test_get_subjects_returns_all_saved_subjects(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    first_id = save_python_subject(database_path)

    second_id = create_subject(
        name="Mathematics",
        difficulty=5,
        deadline=date(2026, 9, 18),
        total_minutes=240,
        database_path=database_path,
    )

    subjects = get_subjects(database_path)

    assert len(subjects) == 2

    assert subjects[0] == {
        "id": first_id,
        "name": "Python",
        "difficulty": 4,
        "deadline": date(2026, 9, 20),
        "total_minutes": 180,
        "remaining_minutes": 180,
    }

    assert subjects[1]["id"] == second_id
    assert subjects[1]["name"] == "Mathematics"


def test_get_subject_returns_subject_with_matching_id(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    subject_id = save_python_subject(database_path)

    subject = get_subject(
        subject_id,
        database_path,
    )

    assert subject == {
        "id": subject_id,
        "name": "Python",
        "difficulty": 4,
        "deadline": date(2026, 9, 20),
        "total_minutes": 180,
        "remaining_minutes": 180,
    }


def test_get_subject_returns_none_for_unknown_id(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    subject = get_subject(
        999,
        database_path,
    )

    assert subject is None



def test_update_subject_changes_saved_values(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    subject_id = save_python_subject(database_path)

    was_updated = update_subject(
        subject_id=subject_id,
        name="Advanced Python",
        difficulty=5,
        deadline=date(2026, 9, 25),
        total_minutes=240,
        database_path=database_path,
    )

    updated_subject = get_subject(
        subject_id,
        database_path,
    )

    assert was_updated is True

    assert updated_subject == {
        "id": subject_id,
        "name": "Advanced Python",
        "difficulty": 5,
        "deadline": date(2026, 9, 25),
        "total_minutes": 240,
        "remaining_minutes": 240,
    }


def test_update_subject_preserves_completed_progress(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    subject_id = save_python_subject(database_path)

    connection = get_connection(database_path)

    try:
        connection.execute(
            """
            UPDATE subjects
            SET remaining_minutes = ?
            WHERE id = ?
            """,
            (120, subject_id),
        )

        connection.commit()

    finally:
        connection.close()

    update_subject(
        subject_id=subject_id,
        name="Python",
        difficulty=4,
        deadline=date(2026, 9, 20),
        total_minutes=240,
        database_path=database_path,
    )

    updated_subject = get_subject(
        subject_id,
        database_path,
    )

    assert updated_subject["total_minutes"] == 240
    assert updated_subject["remaining_minutes"] == 180


def test_update_subject_returns_false_for_unknown_id(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    was_updated = update_subject(
        subject_id=999,
        name="Python",
        difficulty=4,
        deadline=date(2026, 9, 20),
        total_minutes=180,
        database_path=database_path,
    )

    assert was_updated is False


def test_delete_subject_removes_saved_subject(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    subject_id = save_python_subject(database_path)

    was_deleted = delete_subject(
        subject_id,
        database_path,
    )

    assert was_deleted is True
    assert get_subject(subject_id, database_path) is None


def test_delete_subject_returns_false_for_unknown_id(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    was_deleted = delete_subject(
        999,
        database_path,
    )

    assert was_deleted is False


def test_delete_subject_keeps_other_subjects(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    python_id = save_python_subject(database_path)

    math_id = create_subject(
        name="Mathematics",
        difficulty=5,
        deadline=date(2026, 9, 18),
        total_minutes=240,
        database_path=database_path,
    )

    delete_subject(python_id, database_path)

    remaining_subjects = get_subjects(database_path)

    assert len(remaining_subjects) == 1
    assert remaining_subjects[0]["id"] == math_id
    assert remaining_subjects[0]["name"] == "Mathematics"