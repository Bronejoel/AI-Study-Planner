# StudyAI

StudyAI is a Flask web application that creates a seven-day study plan from a
student's subjects, difficulty ratings, deadlines, and available daily hours.

This is the reliable scheduling-engine stage of a larger adaptive AI study
coach. The current planner is a deterministic baseline; it does not yet use a
machine-learning model or an LLM.

## How the current planner works

For each active subject, the planner calculates:

```text
priority = difficulty / remaining days
```

A difficult subject with a close deadline therefore receives more time than an
easy subject with a distant deadline. Each day's available hours are divided in
proportion to these priority scores.

The planner:

- validates all inputs before calculating;
- allocates all available daily time without losing time to rounding;
- stops scheduling a subject after its deadline;
- supports decimal daily hours;
- does not modify the input data; and
- returns friendly web-form errors for invalid data.

## Run the application

Activate the existing virtual environment:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the web application:

```bash
python index.py
```

Open <http://127.0.0.1:5000> in a browser.

## Run the tests

```bash
python -m pytest
```

The test suite checks priority ordering, deadlines, rounding, decimal hours,
input immutability, invalid planner data, and complete Flask form requests.

## Project structure

```text
index.py              Flask route and web-page coordination
planner.py            Validation and scheduling calculations
validation.py         Browser-form parsing
tests/test_planner.py Scheduler unit tests
tests/test_web.py     Flask integration tests
templates/index.html Web page
static/style.css      Page styling
```

## Current limitations

- Availability is the same every day.
- The output uses day numbers instead of calendar dates.
- It allocates time by subject rather than creating practical study sessions.
- It does not track completed work or quiz performance.
- It does not yet answer questions from uploaded notes.

The next milestone is a realistic scheduling model with dates, topic-level
workload, daily availability, and study blocks.
