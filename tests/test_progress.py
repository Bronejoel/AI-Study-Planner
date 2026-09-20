from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import sqlite3

import pytest

import database as db
import progress

TODAY = date(2026, 9, 9)


@pytest.fixture
def path(tmp_path):
    path = tmp_path / 'progress.db'
    progress.initialize_progress(path)
    return path


def seed(path, minutes=180, available=120, name='Python'):
    sid = db.create_subject(name, 4, TODAY + timedelta(days=3), minutes, path)
    progress.save_availability({TODAY: available}, path, TODAY)
    progress.regenerate_plan(path, TODAY)
    return sid


def sessions(path):
    return [entry for entries in progress.dashboard_data(path, TODAY)['days'].values() for entry in entries]


def test_initialization_preserves_existing_subjects(tmp_path):
    path = tmp_path / 'old.db'
    db.initialize_database(path)
    sid = db.create_subject('Python', 4, TODAY, 180, path)
    progress.initialize_progress(path)
    progress.initialize_progress(path)
    assert db.get_subject(sid, path)['remaining_minutes'] == 180


def test_plan_does_not_complete_work_and_regeneration_does_not_duplicate(path):
    sid = seed(path)
    assert db.get_subject(sid, path)['remaining_minutes'] == 180
    for _ in range(3):
        progress.regenerate_plan(path, TODAY)
    assert len(sessions(path)) == 1
    assert sessions(path)[0]['minutes'] == 120


def test_completion_and_partial_regeneration_preserve_history_and_daily_capacity(path):
    sid = seed(path)
    entry = sessions(path)[0]
    progress.record_completion(entry['id'], 30, path, TODAY)
    progress.regenerate_plan(path, TODAY)
    assert db.get_subject(sid, path)['remaining_minutes'] == 150
    assert sum(s['minutes'] for s in sessions(path)) == 120
    assert sum(s['completed_minutes'] for s in sessions(path)) == 30
    assert any(s['id'] == entry['id'] for s in sessions(path))


def test_concurrent_duplicate_completion_counts_once(path):
    sid = seed(path)
    entry = sessions(path)[0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: progress.record_completion(entry['id'], 120, path, TODAY), range(2)))
    assert results == [True, True]
    assert db.get_subject(sid, path)['remaining_minutes'] == 60


def test_undo_restores_workload_and_invalidates_pending_plan(path):
    sid = seed(path)
    entry = sessions(path)[0]
    progress.record_completion(entry['id'], 30, path, TODAY)
    progress.regenerate_plan(path, TODAY)
    progress.record_completion(entry['id'], 0, path, TODAY)
    assert db.get_subject(sid, path)['remaining_minutes'] == 180
    assert sessions(path) == []
    # Repeating an undo for the discarded entry never adds minutes again.
    assert progress.record_completion(entry['id'], 0, path, TODAY) is False
    assert db.get_subject(sid, path)['remaining_minutes'] == 180


def test_same_name_subjects_keep_separate_ids(path):
    first = db.create_subject('Math', 4, TODAY, 60, path)
    second = db.create_subject('Math', 4, TODAY, 60, path)
    progress.save_availability({TODAY: 120}, path, TODAY)
    progress.regenerate_plan(path, TODAY)
    assert {s['subject_id'] for s in sessions(path)} == {first, second}
    chosen = sessions(path)[0]
    progress.record_completion(chosen['id'], 60, path, TODAY)
    remaining = [db.get_subject(sid, path)['remaining_minutes'] for sid in (first, second)]
    assert sorted(remaining) == [0, 60]


def test_delete_cascades_own_history_and_keeps_other_progress(path):
    first = seed(path)
    entry = sessions(path)[0]
    progress.record_completion(entry['id'], 120, path, TODAY)
    second = db.create_subject('Math', 5, TODAY, 60, path)
    db.delete_subject(second, path)
    assert len(sessions(path)) == 1
    assert db.get_subject(first, path)['remaining_minutes'] == 60
    db.delete_subject(first, path)
    assert sessions(path) == []


def test_foreign_keys_reject_orphan_session(path):
    with pytest.raises(sqlite3.IntegrityError):
        with progress.transaction(path) as connection:
            connection.execute("INSERT INTO study_sessions(subject_id, study_date, minutes) VALUES (999, ?, 30)", (TODAY.isoformat(),))


def test_workload_edit_below_completed_is_rejected_without_changes(path):
    sid = seed(path)
    progress.record_completion(sessions(path)[0]['id'], 120, path, TODAY)
    before = db.get_subject(sid, path)
    with pytest.raises(ValueError, match='already completed'):
        db.update_subject(sid, 'Changed', 4, TODAY, 60, path)
    assert db.get_subject(sid, path) == before
    db.update_subject(sid, 'Changed', 4, TODAY, 120, path)
    assert db.get_subject(sid, path)['remaining_minutes'] == 0


@pytest.mark.parametrize('changes', [{'name': ''}, {'difficulty': True}, {'difficulty': 6},
                                   {'total_minutes': -1}, {'total_minutes': 3.5}, {'deadline': 'bad'}])
def test_subject_validation_applies_to_create_and_update(path, changes):
    sid = seed(path)
    values = dict(name='Python', difficulty=4, deadline=TODAY, total_minutes=180)
    values.update(changes)
    with pytest.raises(ValueError):
        db.create_subject(**values, database_path=path)
    with pytest.raises(ValueError):
        db.update_subject(sid, **values, database_path=path)
    assert len(db.get_subjects(path)) == 1


def test_invalid_availability_keeps_saved_plan(path):
    seed(path)
    before = sessions(path)
    with pytest.raises(ValueError):
        progress.save_availability({TODAY: 1500}, path, TODAY)
    assert sessions(path) == before
    progress.record_completion(before[0]['id'], 120, path, TODAY)
    with pytest.raises(ValueError, match='already completed'):
        progress.save_availability({TODAY: 60}, path, TODAY)


def test_cannot_complete_future_session(path):
    seed(path)
    with pytest.raises(ValueError, match='study date'):
        progress.record_completion(sessions(path)[0]['id'], 30, path, TODAY - timedelta(days=1))


def test_missed_work_is_rescheduled_and_expired_work_is_reported(path):
    sid = seed(path)
    tomorrow = TODAY + timedelta(days=1)
    assert progress.dashboard_data(path, tomorrow)['subjects'][0]['unscheduled_minutes'] == 180
    progress.save_availability({tomorrow: 180}, path, tomorrow)
    progress.regenerate_plan(path, tomorrow)
    assert all(s['study_date'] == tomorrow.isoformat() for s in sessions(path))
    expired = TODAY + timedelta(days=5)
    progress.save_availability({expired: 180}, path, expired)
    progress.regenerate_plan(path, expired)
    assert sessions(path) == []
    assert db.get_subject(sid, path)['remaining_minutes'] == 180


def test_failed_regeneration_rolls_back_existing_plan(path, monkeypatch):
    seed(path)
    before = sessions(path)
    def broken(*args, **kwargs):
        raise ValueError('test scheduler failure')
    monkeypatch.setattr(progress, 'generate_realistic_plan', broken)
    with pytest.raises(ValueError):
        progress.regenerate_plan(path, TODAY)
    assert sessions(path) == before
