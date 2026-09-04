from copy import deepcopy
from datetime import date
import pytest

from planner import (
    allocate_study_block,
    calculate_priority,
    calculate_scheduling_priority,
    calculate_study_days_remaining,
    choose_next_subject,
    create_scheduling_subject,
    generate_plan,
    hours_to_minutes,
    schedule_subject_block,
    summarize_sessions,
    generate_daily_schedule,
    generate_realistic_plan,
)


def test_sessions_are_grouped_by_subject_for_display():
    sessions = [
        {"subject": "Math", "minutes": 30},
        {"subject": "Python", "minutes": 30},
        {"subject": "Math", "minutes": 15},
    ]

    result = summarize_sessions(sessions)

    assert result == [
        {"subject": "Math", "session_count": 2, "total_minutes": 45},
        {"subject": "Python", "session_count": 1, "total_minutes": 30},
    ]

def test_realistic_plan_uses_different_daily_availability():
    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 10),
        workload_hours=4,
    )

    availability = {
        date(2026, 9, 5): 60,
        date(2026, 9, 6): 90,
    }

    result = generate_realistic_plan(
        subjects=[subject],
        start_date=date(2026, 9, 5),
        daily_availability=availability,
    )

    assert result["days"][0]["scheduled_minutes"] == 60
    assert result["days"][1]["scheduled_minutes"] == 90


def test_remaining_work_continues_to_next_day():
    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 10),
        workload_hours=2,
    )

    availability = {
        date(2026, 9, 5): 60,
        date(2026, 9, 6): 60,
    }

    result = generate_realistic_plan(
        subjects=[subject],
        start_date=date(2026, 9, 5),
        daily_availability=availability,
    )

    assert result["unfinished_subjects"] == []


def test_realistic_plan_does_not_schedule_after_deadline():
    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 5),
        workload_hours=2,
    )

    availability = {
        date(2026, 9, 5): 60,
        date(2026, 9, 6): 60,
    }

    result = generate_realistic_plan(
        subjects=[subject],
        start_date=date(2026, 9, 5),
        daily_availability=availability,
    )

    assert result["days"][0]["scheduled_minutes"] == 60
    assert result["days"][1]["scheduled_minutes"] == 0


def test_realistic_plan_reports_unfinished_work():
    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 10),
        workload_hours=3,
    )

    availability = {
        date(2026, 9, 5): 60,
    }

    result = generate_realistic_plan(
        subjects=[subject],
        start_date=date(2026, 9, 5),
        daily_availability=availability,
    )

    assert result["unfinished_subjects"] == [
        {
            "name": "Math",
            "remaining_minutes": 120,
        }
    ]

def test_daily_schedule_uses_available_time():
    current_date = date(2026, 9, 5)

    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 10),
        workload_hours=3,
    )

    schedule, updated_subjects = generate_daily_schedule(
        [subject],
        current_date,
        available_minutes=90,
    )

    assert schedule["scheduled_minutes"] == 90
    assert len(schedule["sessions"]) == 3
    assert updated_subjects[0]["remaining_minutes"] == 90


def test_daily_schedule_creates_smaller_final_block():
    current_date = date(2026, 9, 5)

    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 10),
        workload_hours=3,
    )

    schedule, _ = generate_daily_schedule(
        [subject],
        current_date,
        available_minutes=75,
    )

    session_lengths = [
        session["minutes"]
        for session in schedule["sessions"]
    ]

    assert session_lengths == [30, 30, 15]
    assert schedule["scheduled_minutes"] == 75


def test_daily_schedule_stops_when_work_is_complete():
    current_date = date(2026, 9, 5)

    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 10),
        workload_hours=0.25,
    )

    schedule, updated_subjects = generate_daily_schedule(
        [subject],
        current_date,
        available_minutes=60,
    )

    assert schedule["scheduled_minutes"] == 15
    assert len(schedule["sessions"]) == 1
    assert updated_subjects[0]["remaining_minutes"] == 0


def test_daily_schedule_does_not_change_original_subjects():
    current_date = date(2026, 9, 5)

    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 10),
        workload_hours=2,
    )

    generate_daily_schedule(
        [subject],
        current_date,
        available_minutes=60,
    )

    assert subject["remaining_minutes"] == 120

def test_choose_next_subject_returns_highest_priority():
    current_date = date(2026, 9, 5)

    math = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 6),
        workload_hours=3,
    )

    python = create_scheduling_subject(
        name="Python",
        difficulty=2,
        deadline=date(2026, 9, 10),
        workload_hours=2,
    )

    result = choose_next_subject([python, math], current_date)

    assert result["name"] == "Math"


def test_choose_next_subject_ignores_completed_subjects():
    current_date = date(2026, 9, 5)

    completed = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 6),
        workload_hours=3,
    )
    completed["remaining_minutes"] = 0

    unfinished = create_scheduling_subject(
        name="Python",
        difficulty=2,
        deadline=date(2026, 9, 10),
        workload_hours=2,
    )

    result = choose_next_subject(
        [completed, unfinished],
        current_date,
    )

    assert result["name"] == "Python"


def test_choose_next_subject_ignores_expired_subjects():
    current_date = date(2026, 9, 5)

    expired = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 4),
        workload_hours=3,
    )

    available = create_scheduling_subject(
        name="Python",
        difficulty=2,
        deadline=date(2026, 9, 10),
        workload_hours=2,
    )

    result = choose_next_subject(
        [expired, available],
        current_date,
    )

    assert result["name"] == "Python"


def test_choose_next_subject_returns_none_when_nothing_is_available():
    current_date = date(2026, 9, 5)

    result = choose_next_subject([], current_date)

    assert result is None

def test_completed_subject_has_zero_scheduling_priority():
    current_date = date(2026, 9, 5)
    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 10),
        workload_hours=3,
    )
    subject["remaining_minutes"] = 0

    result = calculate_scheduling_priority(subject, current_date)

    assert result == 0

def test_higher_difficulty_creates_higher_scheduling_priority():
    current_date = date(2026, 9, 5)
    deadline = date(2026, 9, 10)

    difficult_subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=deadline,
        workload_hours=3,
    )

    easier_subject = create_scheduling_subject(
        name="English",
        difficulty=2,
        deadline=deadline,
        workload_hours=3,
    )

    difficult_priority = calculate_scheduling_priority(
        difficult_subject,
        current_date,
    )
    easier_priority = calculate_scheduling_priority(
        easier_subject,
        current_date,
    )

    assert difficult_priority > easier_priority

def test_larger_workload_creates_higher_scheduling_priority():
    current_date = date(2026, 9, 5)
    deadline = date(2026, 9, 10)

    large_workload = create_scheduling_subject(
        name="Math",
        difficulty=3,
        deadline=deadline,
        workload_hours=6,
    )

    small_workload = create_scheduling_subject(
        name="Python",
        difficulty=3,
        deadline=deadline,
        workload_hours=2,
    )

    large_priority = calculate_scheduling_priority(
        large_workload,
        current_date,
    )
    small_priority = calculate_scheduling_priority(
        small_workload,
        current_date,
    )

    assert large_priority > small_priority

def test_closer_deadline_creates_higher_scheduling_priority():
    current_date = date(2026, 9, 5)

    close_deadline = create_scheduling_subject(
        name="Math",
        difficulty=3,
        deadline=date(2026, 9, 6),
        workload_hours=3,
    )

    distant_deadline = create_scheduling_subject(
        name="Python",
        difficulty=3,
        deadline=date(2026, 9, 10),
        workload_hours=3,
    )

    close_priority = calculate_scheduling_priority(
        close_deadline,
        current_date,
    )
    distant_priority = calculate_scheduling_priority(
        distant_deadline,
        current_date,
    )

    assert close_priority > distant_priority

def test_scheduling_priority_uses_difficulty_workload_and_deadline():
    current_date = date(2026, 9, 5)
    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 10),
        workload_hours=3,
    )

    result = calculate_scheduling_priority(subject, current_date)

    assert result == pytest.approx(150)

@pytest.mark.parametrize(
    "invalid_subject",
    [
        "Math",
        {},
        {"name": "Math"},
        {"remaining_minutes": 60},
    ],
)
def test_schedule_subject_block_rejects_invalid_subject(invalid_subject):
    with pytest.raises(ValueError):
        schedule_subject_block(invalid_subject)

def test_completed_subject_does_not_create_session():
    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 10),
        workload_hours=1,
    )
    subject["remaining_minutes"] = 0

    session, updated_subject = schedule_subject_block(subject)

    assert session is None
    assert updated_subject["remaining_minutes"] == 0


def test_final_subject_block_can_be_smaller_than_default():
    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 10),
        workload_hours=0.25,
    )

    session, updated_subject = schedule_subject_block(subject)

    assert session["minutes"] == 15
    assert updated_subject["remaining_minutes"] == 0

def test_scheduling_block_does_not_change_original_subject():
    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 10),
        workload_hours=3,
    )

    schedule_subject_block(subject)

    assert subject["remaining_minutes"] == 180

def test_subject_block_creates_session_and_updates_remaining_work():
    subject = create_scheduling_subject(
        name="Math",
        difficulty=5,
        deadline=date(2026, 9, 10),
        workload_hours=3,
    )

    session, updated_subject = schedule_subject_block(subject)

    assert session == {
        "subject": "Math",
        "minutes": 30,
    }
    assert updated_subject["remaining_minutes"] == 150

def test_scheduling_subject_requires_a_python_date():
    with pytest.raises(ValueError, match="Python date"):
        create_scheduling_subject(
            name="Math",
            difficulty=3,
            deadline="2026-09-10",
            workload_hours=2,
        )

@pytest.mark.parametrize(
    "invalid_difficulty",
    [
        0,
        6,
        "hard",
    ],
)
def test_scheduling_subject_rejects_invalid_difficulty(invalid_difficulty):
    with pytest.raises(ValueError):
        create_scheduling_subject(
            name="Math",
            difficulty=invalid_difficulty,
            deadline=date(2026, 9, 10),
            workload_hours=2,
        )

def test_scheduling_subject_requires_a_name():
    with pytest.raises(ValueError, match="name cannot be empty"):
        create_scheduling_subject(
            name="   ",
            difficulty=3,
            deadline=date(2026, 9, 10),
            workload_hours=2,
        )


def test_scheduling_subject_requires_positive_workload():
    with pytest.raises(ValueError, match="greater than 0"):
        create_scheduling_subject(
            name="Math",
            difficulty=3,
            deadline=date(2026, 9, 10),
            workload_hours=0,
        )

def test_scheduling_subject_is_created_with_workload():
    deadline = date(2026, 9, 10)

    result = create_scheduling_subject(
        name="  Math  ",
        difficulty=5,
        deadline=deadline,
        workload_hours=3,
    )

    assert result == {
        "name": "Math",
        "difficulty": 5,
        "deadline": deadline,
        "total_minutes": 180,
        "remaining_minutes": 180,
    }

def test_study_days_include_today_and_deadline():
    current_date = date(2026, 9, 5)
    deadline = date(2026, 9, 10)

    result = calculate_study_days_remaining(deadline, current_date)

    assert result == 6


def test_deadline_today_has_one_study_day():
    current_date = date(2026, 9, 5)
    deadline = date(2026, 9, 5)

    result = calculate_study_days_remaining(deadline, current_date)

    assert result == 1


def test_past_deadline_is_rejected_by_planner():
    current_date = date(2026, 9, 5)
    deadline = date(2026, 9, 4)

    with pytest.raises(ValueError, match="cannot be in the past"):
        calculate_study_days_remaining(deadline, current_date)


#time covertion test
def test_decimal_hours_are_converted_to_minutes():
    result = hours_to_minutes(1.5)

    assert result == 90


def test_quarter_hour_is_converted_to_minutes():
    result = hours_to_minutes(0.25)

    assert result == 15


def test_zero_hours_are_allowed():
    result = hours_to_minutes(0)

    assert result == 0

@pytest.mark.parametrize(
    "invalid_hours",
    [
        -1,
        "two",
        None,
        float("inf"),
        float("nan"),
    ],
)
def test_invalid_hours_are_rejected(invalid_hours):
    with pytest.raises(ValueError):
        hours_to_minutes(invalid_hours)

#allocation test
def test_full_study_block_is_allocated():
    scheduled, remaining = allocate_study_block(90)

    assert scheduled == 30
    assert remaining == 60


def test_final_study_block_does_not_exceed_remaining_work():
    scheduled, remaining = allocate_study_block(20)

    assert scheduled == 20
    assert remaining == 0


def test_completed_subject_receives_no_more_time():
    scheduled, remaining = allocate_study_block(0)

    assert scheduled == 0
    assert remaining == 0

@pytest.mark.parametrize(
    "remaining_minutes,block_minutes",
    [
        (-1, 30),
        (60, 0),
        (60, -30),
        ("60", 30),
        (60, 30.5),
    ],
)
def test_invalid_study_block_values_are_rejected(
    remaining_minutes,
    block_minutes,
):
    with pytest.raises(ValueError):
        allocate_study_block(remaining_minutes, block_minutes)
#Done

def subject(name="Math", difficulty=3, days_left=5):
    """Create a subject with sensible defaults for a test."""
    return {
        "name": name,
        "difficulty": difficulty,
        "days_left": days_left,
    }


def allocation_for(day, subject_name):
    """Return the allocated hours for one subject on one day."""
    return next(
        item["hours"] for item in day["plan"] if item["name"] == subject_name
    )


def test_more_difficult_subject_has_higher_priority():
    easy = subject(name="English", difficulty=2)
    hard = subject(name="Math", difficulty=5)

    assert calculate_priority(hard) > calculate_priority(easy)


def test_closer_deadline_has_higher_priority():
    later = subject(name="English", days_left=10)
    sooner = subject(name="Math", days_left=2)

    assert calculate_priority(sooner) > calculate_priority(later)


def test_daily_allocations_use_all_available_hours():
    subjects = [
        subject(name="Math"),
        subject(name="English"),
        subject(name="Python"),
    ]

    plan = generate_plan(subjects, hours_per_day=1)

    for day in plan:
        if day["plan"]:
            allocated = sum(item["hours"] for item in day["plan"])
            assert allocated == pytest.approx(1)


def test_subject_is_not_scheduled_after_its_deadline():
    plan = generate_plan([subject(days_left=1)], hours_per_day=2)

    assert len(plan[0]["plan"]) == 1
    assert all(day["plan"] == [] for day in plan[1:])


def test_generate_plan_does_not_change_original_subjects():
    subjects = [subject(days_left=5)]
    original = deepcopy(subjects)

    generate_plan(subjects, hours_per_day=2)

    assert subjects == original


@pytest.mark.parametrize(
    "subjects,hours_per_day",
    [
        ([], 2),
        ([subject(days_left=0)], 2),
        ([subject(difficulty=0)], 2),
        ([subject(difficulty=6)], 2),
        ([subject()], 0),
        ([subject()], float("inf")),
        ([subject()], float("nan")),
    ],
)
def test_invalid_planner_input_is_rejected(subjects, hours_per_day):
    with pytest.raises(ValueError):
        generate_plan(subjects, hours_per_day)


def test_decimal_daily_hours_are_supported():
    plan = generate_plan([subject()], hours_per_day=1.5)

    assert allocation_for(plan[0], "Math") == pytest.approx(1.5)
