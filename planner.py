from math import floor, isfinite


PLAN_DAYS = 7
HOUR_UNITS = 100


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
