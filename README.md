# StudyAI

StudyAI is a Flask web application that creates a deadline-aware study plan from
a student's subjects, difficulty ratings, remaining workload, and availability
on specific calendar dates.

This is the reliable scheduling-engine stage of a larger adaptive AI study
coach. The current planner is a deterministic baseline; it does not yet use a
machine-learning model or an LLM.

## How the current planner works

For each unfinished subject that has not passed its deadline, the planner
calculates:

```text
required daily minutes = remaining minutes / remaining study days
priority = difficulty * required daily minutes
```

A difficult subject with substantial remaining work and a close deadline
therefore receives a study block before a less urgent subject. Priorities are
recalculated as work is scheduled.

The planner:

- validates all inputs before calculating;
- supports different availability on each calendar date;
- allows availability dates beyond the initial seven suggested dates;
- creates 30-minute sessions with a shorter final session when necessary;
- stops scheduling a subject after its deadline;
- stops scheduling a subject when its workload is complete;
- groups repeated sessions into readable daily summaries;
- reports work that could not be scheduled;
- preserves submitted form values after success or validation errors;
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

Open <http://127.0.0.1:5001> in a browser.

## Run the tests

```bash
python -m pytest
```

The test suite checks date and form parsing, priority ordering, deadline rules,
workload updates, session allocation, input immutability, dynamic availability,
grouped output, unfinished-work warnings, and complete Flask requests.

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

- Sessions use a fixed default size of 30 minutes.
- Availability records total daily hours rather than specific clock times.
- Plans are not saved between requests because there is no database yet.
- It does not track completed work or quiz performance.
- It does not yet answer questions from uploaded notes.

The next milestone is persistent progress tracking with a database, followed by
note retrieval and grounded AI assistance.
