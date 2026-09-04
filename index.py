from datetime import date, timedelta

from flask import Flask, render_template, request

from planner import generate_realistic_plan
from validation import parse_realistic_plan_form


app = Flask(__name__)


def format_duration(total_minutes):
    """Format minutes as a compact human-readable duration."""
    hours, minutes = divmod(total_minutes, 60)
    parts = []

    if hours:
        parts.append(f"{hours} hr")
    if minutes or not parts:
        parts.append(f"{minutes} min")

    return " ".join(parts)


app.jinja_env.filters["duration"] = format_duration


def create_planning_dates(start_date, number_of_days=7):
    """Create consecutive dates for the availability form."""

    return [
        start_date + timedelta(days=offset)
        for offset in range(number_of_days)
    ]


def create_subject_rows(form=None):
    """Create template rows, preserving submitted subject values."""
    if form is None:
        return [{"name": "", "difficulty": "", "deadline": "", "workload": ""}]

    values = {
        "name": form.getlist("name"),
        "difficulty": form.getlist("difficulty"),
        "deadline": form.getlist("deadline"),
        "workload": form.getlist("workload"),
    }
    row_count = max(1, *(len(items) for items in values.values()))

    return [
        {
            field: items[index] if index < len(items) else ""
            for field, items in values.items()
        }
        for index in range(row_count)
    ]


def create_availability_rows(today, form=None):
    """Create editable availability rows, preserving submitted values."""
    if form is None:
        return [
            {"date": planning_date.isoformat(), "hours": "0"}
            for planning_date in create_planning_dates(today)
        ]

    dates = form.getlist("availability_date")
    hours = form.getlist("availability_hours")
    row_count = max(1, len(dates), len(hours))

    return [
        {
            "date": dates[index] if index < len(dates) else "",
            "hours": hours[index] if index < len(hours) else "0",
        }
        for index in range(row_count)
    ]


def create_template_context(today, form=None, **extra_values):
    """Build the common values required by the page template."""
    return {
        "today": today,
        "subject_rows": create_subject_rows(form),
        "availability_rows": create_availability_rows(today, form),
        **extra_values,
    }


@app.route("/", methods=["GET", "POST"])
def home():
    today = date.today()

    if request.method == "POST":
        try:
            form_data = parse_realistic_plan_form(
                request.form,
                today=today,
            )

            plan = generate_realistic_plan(
                subjects=form_data["subjects"],
                start_date=form_data["start_date"],
                daily_availability=form_data["daily_availability"],
            )

        except ValueError as error:
            return render_template(
                "index.html",
                **create_template_context(
                    today,
                    request.form,
                    error=str(error),
                ),
            ), 400

        return render_template(
            "index.html",
            **create_template_context(
                today,
                request.form,
                plan=plan,
            ),
        )

    return render_template(
        "index.html",
        **create_template_context(today),
    )


if __name__ == "__main__":
    app.run(debug=False, port=5001)
