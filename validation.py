
from datetime import date
from math import isfinite

from planner import (
    create_scheduling_subject,
    hours_to_minutes,
    validate_plan_input,
)
def parse_deadline(deadline_text, today=None):
    """Convert a browser date string into a validated Python date."""

    if not isinstance(deadline_text, str) or not deadline_text.strip():
        raise ValueError("Choose a deadline date.")

    try:
        deadline = date.fromisoformat(deadline_text.strip())
    except ValueError as error:
        raise ValueError("Deadline must be a valid date.") from error

    if today is None:
        today = date.today()

    if deadline < today:
        raise ValueError("Deadline cannot be in the past.")

    return deadline

def parse_daily_availability(
    date_values,
    hour_values,
    today=None,
):
    """Convert availability form values into dates and minutes."""

    if len(date_values) != len(hour_values):
        raise ValueError(
            "Every availability date needs a number of hours."
        )

    if not date_values:
        raise ValueError("Add at least one availability date.")

    availability = {}

    for row_number, (date_text, hours_text) in enumerate(
        zip(date_values, hour_values),
        start=1,
    ):
        date_text = date_text.strip() if isinstance(date_text, str) else ""
        hours_text = hours_text.strip() if isinstance(hours_text, str) else ""

        # A newly added row may be left unused. Ignore it when it has no date
        # and no meaningful amount of available time.
        if not date_text and hours_text in {"", "0", "0.0", "0.00"}:
            continue

        if not date_text:
            raise ValueError(
                f"Choose a study date for availability row {row_number}."
            )

        study_date = parse_deadline(date_text, today=today)

        if study_date in availability:
            raise ValueError(
                f"Availability date {study_date} was entered twice."
            )

        if not hours_text:
            raise ValueError(
                f"Enter available hours for row {row_number}."
            )

        try:
            hours = float(hours_text)
        except ValueError as error:
            raise ValueError(
                f"Available hours for row {row_number} must be a number."
            ) from error

        minutes = hours_to_minutes(hours)
        availability[study_date] = minutes

    if not availability:
        raise ValueError("Add at least one study date and your available hours.")

    return availability


def parse_scheduling_subjects(form, today=None):
    """Convert Phase 2 subject form rows into scheduling subjects."""

    names = form.getlist("name")
    difficulties = form.getlist("difficulty")
    deadlines = form.getlist("deadline")
    workloads = form.getlist("workload")

    field_lengths = {
        len(names),
        len(difficulties),
        len(deadlines),
        len(workloads),
    }

    if len(field_lengths) != 1:
        raise ValueError(
            "Every subject needs a name, difficulty, deadline, and workload."
        )

    subjects = []

    for row_number, (
        name,
        difficulty_text,
        deadline_text,
        workload_text,
    ) in enumerate(
        zip(names, difficulties, deadlines, workloads),
        start=1,
    ):
        values = [
            name.strip(),
            difficulty_text.strip(),
            deadline_text.strip(),
            workload_text.strip(),
        ]

        if not any(values):
            continue

        if not all(values):
            raise ValueError(
                f"Complete all fields for subject {row_number}."
            )

        try:
            difficulty = int(difficulty_text)
        except ValueError as error:
            raise ValueError(
                f"Difficulty for subject {row_number} must be a whole number."
            ) from error

        try:
            workload_hours = float(workload_text)
        except ValueError as error:
            raise ValueError(
                f"Workload for subject {row_number} must be a number."
            ) from error

        deadline = parse_deadline(
            deadline_text,
            today=today,
        )

        subject = create_scheduling_subject(
            name=name,
            difficulty=difficulty,
            deadline=deadline,
            workload_hours=workload_hours,
        )

        subjects.append(subject)

    if not subjects:
        raise ValueError("Add at least one subject.")

    return subjects

def parse_realistic_plan_form(form, today=None):
    """Parse everything required by the Phase 2 scheduler."""

    if today is None:
        today = date.today()

    subjects = parse_scheduling_subjects(
        form,
        today=today,
    )

    daily_availability = parse_daily_availability(
        date_values=form.getlist("availability_date"),
        hour_values=form.getlist("availability_hours"),
        today=today,
    )

    return {
        "subjects": subjects,
        "start_date": today,
        "daily_availability": daily_availability,
    }

def parse_plan_form(form):
    """Convert browser form text into validated planner data."""
    names = form.getlist("name")
    difficulties = form.getlist("difficulty")
    days_values = form.getlist("days")

    if not (len(names) == len(difficulties) == len(days_values)):
        raise ValueError("Each subject needs a name, difficulty, and deadline.")

    subjects = []
    for row_number, (name, difficulty_text, days_text) in enumerate(
        zip(names, difficulties, days_values), start=1
    ):
        name = name.strip()
        difficulty_text = difficulty_text.strip()
        days_text = days_text.strip()

        # Ignore a completely blank row, but reject a partially completed row.
        if not name and not difficulty_text and not days_text:
            continue
        if not name or not difficulty_text or not days_text:
            raise ValueError(f"Complete all fields for subject {row_number}.")

        try:
            difficulty = int(difficulty_text)
            days_left = int(days_text)
        except ValueError as error:
            raise ValueError(
                f"Difficulty and days left for subject {row_number} must be whole numbers."
            ) from error

        subjects.append(
            {
                "name": name,
                "difficulty": difficulty,
                "days_left": days_left,
            }
        )

    hours_text = form.get("hours", "").strip()
    try:
        hours_per_day = float(hours_text)
    except ValueError as error:
        raise ValueError("Study hours must be a number.") from error

    if not isfinite(hours_per_day):
        raise ValueError("Study hours must be a finite number.")

    validate_plan_input(subjects, hours_per_day)
    return subjects, hours_per_day
