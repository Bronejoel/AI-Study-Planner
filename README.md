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

## Phase 3: saved progress

Subjects, daily availability, and study sessions now persist in SQLite. You can
edit or delete subjects, record partial or full session completion, undo it, and
regenerate pending work without losing completed history.

Scheduling is not completion: generating a plan does not reduce actual remaining
work. Only recording progress does. Regeneration subtracts time already studied
from each day's availability. Future sessions cannot be marked complete.

Changing subjects or availability clears pending sessions; generate again to
rebuild them. Undo also clears pending sessions so restored work can be scheduled
again. Deleting a subject permanently deletes its associated session history.

## Run the application

Open a terminal in the project folder:

```bash
cd /Users/bronejoel/Desktop/PythonProjects/ai-study-planner
```

Activate the existing virtual environment:

```bash
source venv/bin/activate
```

On a fresh clone, first create the environment with `python3 -m venv venv`.

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the web application:

```bash
python index.py
```

Open <http://127.0.0.1:5001> in a browser.

The first request initializes any missing database tables without replacing
existing subjects. `study_ai.db` lives beside `database.py`; it is a binary SQLite
file, not a Python or text file. Do not edit it in the text editor. The database
and its temporary journal files are excluded from Git. Back it up separately
while the app is stopped if you need to preserve your personal progress.

Use the app in this order: save subjects, save availability, generate a plan,
then record work as you finish it. Durations are displayed compactly, for example
`1 hr 30 min`. After restarting the server, refresh the page before submitting
an old form. For a stable session secret, set the `STUDYAI_SECRET_KEY` environment
variable to a private random value; do not commit it.

## Run the tests

```bash
python -m pytest
```

The tests cover scheduler rules, validation, database persistence, progress and
undo, regeneration, concurrent duplicate completion, and complete Flask requests.
Database and web tests use temporary databases, not your personal study data.

## Project structure

```text
index.py                 Flask app factory, routes, form protection
database.py              SQLite connections, subject storage, validation
progress.py              Saved availability, sessions, progress, regeneration
planner.py               Scheduling calculations
validation.py            Browser-form parsing
templates/dashboard.html Current saved-progress web page
templates/request_error.html Friendly request errors
static/style.css         Page styling
tests/                   Scheduler, validation, database and web tests
docs/phase3-guide.md      Beginner-friendly explanation of Phase 3
```

## Current limitations

- Sessions use a fixed default size of 30 minutes.
- Availability records total daily hours rather than specific clock times.
- This is a single-user local app: there are no accounts or login isolation.
- Do not expose it publicly as a multi-user service without authentication,
  authorization, deployment hardening, and a suitable production server.
- Completion is self-reported; the app does not detect studying automatically.
- It does not track quiz performance.
- It does not yet answer questions from uploaded notes.

Possible later milestones include user accounts, note retrieval, and grounded AI
assistance. See [the Phase 3 learning guide](docs/phase3-guide.md) to understand the
current implementation before moving on.
