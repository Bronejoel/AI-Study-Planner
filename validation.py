from math import isfinite

from planner import validate_plan_input


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
