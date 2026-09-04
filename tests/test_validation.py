from datetime import date

import pytest
from werkzeug.datastructures import MultiDict

from validation import (
    parse_daily_availability,
    parse_deadline,
    parse_scheduling_subjects,
    parse_realistic_plan_form,
)

def test_realistic_plan_form_parses_all_required_data():
    fixed_today = date(2026, 9, 5)

    form = MultiDict([
        ("name", "Math"),
        ("difficulty", "5"),
        ("deadline", "2026-09-10"),
        ("workload", "3"),
        ("availability_date", "2026-09-05"),
        ("availability_hours", "2"),
        ("availability_date", "2026-09-06"),
        ("availability_hours", "1.5"),
    ])

    result = parse_realistic_plan_form(
        form,
        today=fixed_today,
    )

    assert result["start_date"] == fixed_today

    assert result["subjects"][0]["name"] == "Math"
    assert result["subjects"][0]["total_minutes"] == 180

    assert result["daily_availability"] == {
        date(2026, 9, 5): 120,
        date(2026, 9, 6): 90,
    }
def test_scheduling_subjects_are_parsed_from_form():
    fixed_today = date(2026, 9, 5)

    form = MultiDict([
        ("name", "Math"),
        ("difficulty", "5"),
        ("deadline", "2026-09-10"),
        ("workload", "3"),
        ("name", "Python"),
        ("difficulty", "3"),
        ("deadline", "2026-09-12"),
        ("workload", "1.5"),
    ])

    result = parse_scheduling_subjects(
        form,
        today=fixed_today,
    )

    assert len(result) == 2

    assert result[0] == {
        "name": "Math",
        "difficulty": 5,
        "deadline": date(2026, 9, 10),
        "total_minutes": 180,
        "remaining_minutes": 180,
    }

    assert result[1]["name"] == "Python"
    assert result[1]["total_minutes"] == 90

def test_incomplete_scheduling_subject_is_rejected():
    fixed_today = date(2026, 9, 5)

    form = MultiDict([
        ("name", "Math"),
        ("difficulty", "5"),
        ("deadline", ""),
        ("workload", "3"),
    ])

    with pytest.raises(ValueError, match="Complete all fields"):
        parse_scheduling_subjects(
            form,
            today=fixed_today,
        )

def test_scheduling_subject_form_requires_a_subject():
    form = MultiDict([
        ("name", ""),
        ("difficulty", ""),
        ("deadline", ""),
        ("workload", ""),
    ])

    with pytest.raises(ValueError, match="at least one subject"):
        parse_scheduling_subjects(form)

@pytest.mark.parametrize(
    "difficulty,workload",
    [
        ("hard", "3"),
        ("5", "many"),
        ("0", "3"),
        ("6", "3"),
        ("5", "0"),
    ],
)
def test_invalid_scheduling_subject_values_are_rejected(
    difficulty,
    workload,
):
    fixed_today = date(2026, 9, 5)

    form = MultiDict([
        ("name", "Math"),
        ("difficulty", difficulty),
        ("deadline", "2026-09-10"),
        ("workload", workload),
    ])

    with pytest.raises(ValueError):
        parse_scheduling_subjects(
            form,
            today=fixed_today,
        )

def test_daily_availability_is_converted_to_minutes():
    fixed_today = date(2026, 9, 5)

    result = parse_daily_availability(
        date_values=["2026-09-05", "2026-09-06"],
        hour_values=["1.5", "2"],
        today=fixed_today,
    )

    assert result == {
        date(2026, 9, 5): 90,
        date(2026, 9, 6): 120,
    }


def test_zero_daily_availability_is_allowed():
    fixed_today = date(2026, 9, 5)

    result = parse_daily_availability(
        date_values=["2026-09-05"],
        hour_values=["0"],
        today=fixed_today,
    )

    assert result == {
        date(2026, 9, 5): 0,
    }

def test_duplicate_availability_dates_are_rejected():
    fixed_today = date(2026, 9, 5)

    with pytest.raises(ValueError, match="entered twice"):
        parse_daily_availability(
            date_values=["2026-09-05", "2026-09-05"],
            hour_values=["1", "2"],
            today=fixed_today,
        )

def test_availability_requires_at_least_one_date():
    with pytest.raises(ValueError, match="at least one"):
        parse_daily_availability(
            date_values=[],
            hour_values=[],
        )


def test_every_availability_date_requires_hours():
    fixed_today = date(2026, 9, 5)

    with pytest.raises(ValueError, match="needs a number of hours"):
        parse_daily_availability(
            date_values=["2026-09-05", "2026-09-06"],
            hour_values=["1"],
            today=fixed_today,
        )


@pytest.mark.parametrize("unused_hours", ["", "0", "0.0", "0.00"])
def test_unused_blank_availability_row_is_ignored(unused_hours):
    fixed_today = date(2026, 9, 5)

    result = parse_daily_availability(
        date_values=["2026-09-05", ""],
        hour_values=["1.5", unused_hours],
        today=fixed_today,
    )

    assert result == {date(2026, 9, 5): 90}


def test_availability_hours_without_a_date_has_a_clear_error():
    fixed_today = date(2026, 9, 5)

    with pytest.raises(
        ValueError,
        match="Choose a study date for availability row 2",
    ):
        parse_daily_availability(
            date_values=["2026-09-05", ""],
            hour_values=["1", "2"],
            today=fixed_today,
        )


def test_availability_requires_at_least_one_completed_row():
    fixed_today = date(2026, 9, 5)

    with pytest.raises(ValueError, match="Add at least one study date"):
        parse_daily_availability(
            date_values=[""],
            hour_values=[""],
            today=fixed_today,
        )


@pytest.mark.parametrize(
    "invalid_hours",
    [
        "",
        "many",
        "-1",
        "inf",
    ],
)
def test_invalid_availability_hours_are_rejected(invalid_hours):
    fixed_today = date(2026, 9, 5)

    with pytest.raises(ValueError):
        parse_daily_availability(
            date_values=["2026-09-05"],
            hour_values=[invalid_hours],
            today=fixed_today,
        )

def test_parse_deadline_returns_a_python_date():
    fixed_today = date(2026, 9, 5)

    result = parse_deadline("2026-09-10", today=fixed_today)

    assert result == date(2026, 9, 10)


def test_deadline_can_be_today():
    fixed_today = date(2026, 9, 5)

    result = parse_deadline("2026-09-05", today=fixed_today)

    assert result == fixed_today


@pytest.mark.parametrize(
    "invalid_value",
    [
        "",
        "not-a-date",
        "05/09/2026",
    ],
)
def test_invalid_deadline_is_rejected(invalid_value):
    fixed_today = date(2026, 9, 5)

    with pytest.raises(ValueError):
        parse_deadline(invalid_value, today=fixed_today)


def test_past_deadline_is_rejected():
    fixed_today = date(2026, 9, 5)

    with pytest.raises(ValueError, match="cannot be in the past"):
        parse_deadline("2026-09-04", today=fixed_today)
