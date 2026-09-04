from copy import deepcopy

import pytest

from planner import calculate_priority, generate_plan


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
