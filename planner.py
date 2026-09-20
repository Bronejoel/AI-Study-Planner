from datetime import date
from math import floor, isfinite

PLAN_DAYS = 7
HOUR_UNITS = 100
MINUTES_PER_HOUR = 60
DEFAULT_BLOCK_MINUTES = 30

def calculate_study_days_remaining(deadline, current_date):
    """Count the usable study dates, including today and the deadline."""

    if deadline < current_date:
        raise ValueError("Deadline cannot be in the past.")

    date_difference = deadline - current_date

    return date_difference.days + 1

def hours_to_minutes(hours):
    """Convert a non-negative number of hours into whole minutes."""

    if isinstance(hours, bool) or not isinstance(hours, (int, float)):
        raise ValueError("Hours must be a number.")

    if not isfinite(hours):
        raise ValueError("Hours must be a finite number.")

    if hours < 0:
        raise ValueError("Hours cannot be negative.")

    minutes = round(hours * MINUTES_PER_HOUR)

    return minutes


def create_scheduling_subject(
    name,
    difficulty,
    deadline,
    workload_hours,
):
    """Create a validated subject for the realistic scheduler."""

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Subject name cannot be empty.")

    if isinstance(difficulty, bool) or not isinstance(difficulty, (int, float)):
        raise ValueError("Difficulty must be a number between 1 and 5.")

    if not 1 <= difficulty <= 5:
        raise ValueError("Difficulty must be between 1 and 5.")

    if not isinstance(deadline, date):
        raise ValueError("Deadline must be a Python date.")

    workload_minutes = hours_to_minutes(workload_hours)

    if workload_minutes <= 0:
        raise ValueError("Workload must be greater than 0.")

    return {
        "name": name.strip(),
        "difficulty": difficulty,
        "deadline": deadline,
        "total_minutes": workload_minutes,
        "remaining_minutes": workload_minutes,
    }

def calculate_scheduling_priority(subject, current_date):
    """Calculate priority using difficulty, workload, and deadline."""

    study_days_remaining = calculate_study_days_remaining(
        subject["deadline"],
        current_date,
    )

    required_daily_minutes = (
        subject["remaining_minutes"] / study_days_remaining
    )

    priority = subject["difficulty"] * required_daily_minutes

    return priority

def choose_next_subject(subjects, current_date):
    """Choose the highest-priority unfinished subject."""

    eligible_subjects = [
        subject
        for subject in subjects
        if subject["remaining_minutes"] > 0
        and subject["deadline"] >= current_date
    ]

    if not eligible_subjects:
        return None

    return max(
        eligible_subjects,
        key=lambda subject: calculate_scheduling_priority(
            subject,
            current_date,
        ),
    )


def summarize_sessions(sessions):
    """Group repeated session blocks by subject for display."""
    summaries_by_subject = {}

    for session in sessions:
        subject_name = session["subject"]

        if subject_name not in summaries_by_subject:
            summaries_by_subject[subject_name] = {
                "subject": subject_name,
                "session_count": 0,
                "total_minutes": 0,
            }

        summary = summaries_by_subject[subject_name]
        summary["session_count"] += 1
        summary["total_minutes"] += session["minutes"]

    return list(summaries_by_subject.values())

def generate_daily_schedule(
    subjects,
    current_date,
    available_minutes,
    block_minutes=DEFAULT_BLOCK_MINUTES,
):
    """Fill one day with the highest-priority study blocks."""

    if isinstance(available_minutes, bool) or not isinstance(
        available_minutes,
        int,
    ):
        raise ValueError("Available minutes must be a whole number.")

    if available_minutes < 0:
        raise ValueError("Available minutes cannot be negative.")

    if isinstance(block_minutes, bool) or not isinstance(block_minutes, int):
        raise ValueError("Block minutes must be a whole number.")

    if block_minutes <= 0:
        raise ValueError("Block minutes must be greater than 0.")

    updated_subjects = [subject.copy() for subject in subjects]
    sessions = []
    remaining_availability = available_minutes

    while remaining_availability > 0:
        chosen_subject = choose_next_subject(
            updated_subjects,
            current_date,
        )

        if chosen_subject is None:
            break

        available_block = min(
            block_minutes,
            remaining_availability,
        )

        session, updated_subject = schedule_subject_block(
            chosen_subject,
            available_block,
        )

        if session is None:
            break

        session["date"] = current_date
        sessions.append(session)

        chosen_index = next(
            index
            for index, subject in enumerate(updated_subjects)
            if subject is chosen_subject
        )

        updated_subjects[chosen_index] = updated_subject
        remaining_availability -= session["minutes"]

    daily_schedule = {
        "date": current_date,
        "sessions": sessions,
        "session_summary": summarize_sessions(sessions),
        "scheduled_minutes": sum(
            session["minutes"] for session in sessions
        ),
    }

    return daily_schedule, updated_subjects

def generate_realistic_plan(
    subjects,
    start_date,
    daily_availability,
    block_minutes=DEFAULT_BLOCK_MINUTES,
):
    """Generate study sessions across several calendar dates."""

    if not isinstance(daily_availability, dict):
        raise ValueError("Daily availability must be a dictionary.")

    updated_subjects = [subject.copy() for subject in subjects]
    daily_schedules = []

    study_dates = sorted(
        study_date
        for study_date in daily_availability
        if study_date >= start_date
    )

    for study_date in study_dates:
        daily_schedule, updated_subjects = generate_daily_schedule(
            subjects=updated_subjects,
            current_date=study_date,
            available_minutes=daily_availability[study_date],
            block_minutes=block_minutes,
        )

        daily_schedules.append(daily_schedule)

    unfinished_subjects = [
        {
            "name": subject["name"],
            "remaining_minutes": subject["remaining_minutes"],
        }
        for subject in updated_subjects
        if subject["remaining_minutes"] > 0
    ]

    return {
        "days": daily_schedules,
        "unfinished_subjects": unfinished_subjects,
    }

def allocate_study_block(
    remaining_minutes,
    block_minutes=DEFAULT_BLOCK_MINUTES,
):
    """Allocate one study block without exceeding the remaining workload."""

    if isinstance(remaining_minutes, bool) or not isinstance(remaining_minutes, int):
        raise ValueError("Remaining minutes must be a whole number.")

    if isinstance(block_minutes, bool) or not isinstance(block_minutes, int):
        raise ValueError("Block minutes must be a whole number.")

    if remaining_minutes < 0:
        raise ValueError("Remaining minutes cannot be negative.")

    if block_minutes <= 0:
        raise ValueError("Block minutes must be greater than 0.")

    scheduled_minutes = min(remaining_minutes, block_minutes)
    new_remaining_minutes = remaining_minutes - scheduled_minutes

    return scheduled_minutes, new_remaining_minutes

def schedule_subject_block(
    subject,
    block_minutes=DEFAULT_BLOCK_MINUTES,
):
    """Create one study session and return an updated subject copy."""

    if not isinstance(subject, dict):
        raise ValueError("Subject must be a dictionary.")

    if "name" not in subject or "remaining_minutes" not in subject:
        raise ValueError(
            "Subject must contain a name and remaining minutes."
        )

    scheduled_minutes, new_remaining_minutes = allocate_study_block(
        subject["remaining_minutes"],
        block_minutes,
    )

    updated_subject = subject.copy()
    updated_subject["remaining_minutes"] = new_remaining_minutes

    if scheduled_minutes == 0:
        return None, updated_subject

    session = {
        "subject": subject["name"],
        "minutes": scheduled_minutes,
    }
    if "id" in subject:
        session["subject_id"] = subject["id"]

    return session, updated_subject

def calculate_priority(subject, days_remaining=None):
    """Return a larger score for harder subjects with closer deadlines."""
    difficulty = subject["difficulty"]
    days = subject["days_left"] if days_remaining is None else days_remaining

    if not 1 <= difficulty <= 5:
        raise ValueError("Difficulty must be between 1 and 5.")
    if days < 1:
        raise ValueError("Days left must be at least 1.")

    return difficulty / days


def validate_plan_input(subjects, hours_per_day):
    """Raise a clear error when the planner receives unusable data."""
    if not subjects:
        raise ValueError("Add at least one subject.")

    if isinstance(hours_per_day, bool) or not isinstance(hours_per_day, (int, float)):
        raise ValueError("Study hours must be a number.")
    if not isfinite(hours_per_day):
        raise ValueError("Study hours must be a finite number.")
    if hours_per_day <= 0:
        raise ValueError("Study hours must be greater than 0.")

    for subject in subjects:
        name = subject.get("name")
        difficulty = subject.get("difficulty")
        days_left = subject.get("days_left")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Every subject needs a name.")
        if isinstance(difficulty, bool) or not isinstance(difficulty, (int, float)):
            raise ValueError("Difficulty must be a number between 1 and 5.")
        if not 1 <= difficulty <= 5:
            raise ValueError("Difficulty must be between 1 and 5.")
        if isinstance(days_left, bool) or not isinstance(days_left, int):
            raise ValueError("Days left must be a whole number.")
        if days_left < 1:
            raise ValueError("Days left must be at least 1.")


def allocate_hours(subjects, priorities, hours_per_day):
    """Allocate all available time in hundredths of an hour."""
    available_units = round(hours_per_day * HOUR_UNITS)
    total_priority = sum(priorities)
    exact_units = [
        priority / total_priority * available_units for priority in priorities
    ]

    allocated_units = [floor(units) for units in exact_units]
    units_left = available_units - sum(allocated_units)

    # Give leftover units to subjects with the largest fractional remainder.
    remainder_order = sorted(
        range(len(subjects)),
        key=lambda index: exact_units[index] - allocated_units[index],
        reverse=True,
    )
    for index in remainder_order[:units_left]:
        allocated_units[index] += 1

    return [
        {
            "name": subject["name"],
            "hours": units / HOUR_UNITS,
        }
        for subject, units in zip(subjects, allocated_units)
    ]


def generate_plan(subjects, hours_per_day):
    """Generate a seven-day plan without changing the supplied subjects."""
    validate_plan_input(subjects, hours_per_day)
    weekly_plan = []

    for day_number in range(1, PLAN_DAYS + 1):
        active_subjects = [
            subject for subject in subjects if subject["days_left"] >= day_number
        ]

        if not active_subjects:
            weekly_plan.append({"day": day_number, "plan": []})
            continue

        active_subjects = sorted(
            active_subjects,
            key=lambda subject: calculate_priority(
                subject,
                days_remaining=subject["days_left"] - day_number + 1,
            ),
            reverse=True,
        )
        priorities = [
            calculate_priority(
                subject,
                days_remaining=subject["days_left"] - day_number + 1,
            )
            for subject in active_subjects
        ]

        daily_plan = allocate_hours(active_subjects, priorities, hours_per_day)
        weekly_plan.append({"day": day_number, "plan": daily_plan})

    return weekly_plan
