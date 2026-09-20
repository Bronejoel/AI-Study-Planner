# Phase 3: how your app remembers progress

## What changed?

Phase 2 calculated a plan from a form. Phase 3 gives the app a memory: saved
subjects, available study hours, planned sessions, and actual completed work.
Closing the browser or restarting Python no longer loses those records.

This is still your Flask application with HTML, CSS and a little JavaScript.
There is no React, FastAPI, login system, or AI model in this phase.

## One example to understand the logic

1. Save Python with a total workload of 3 hours: the database stores 180 minutes.
2. Generate a plan: it might schedule 90 minutes today and 90 tomorrow.
3. Remaining work is still 180 minutes. A plan is a promise, not completed work.
4. Record 30 minutes completed today: remaining work becomes 150 minutes.
5. Generate again: those 30 minutes remain in history. If today's availability
   was 90 minutes, only 60 minutes of today's capacity remain for new work.
6. Undo the completion: remaining work returns to 180. Pending sessions are
   cleared; generate again to place that restored work into a new plan.

The central rule is `remaining = total workload - actual completed work`.

## Where the information lives

`study_ai.db` is the SQLite database file beside `database.py`. SQLite stores
structured records in tables, rather like sheets of rows and columns. It is a
binary file, so strange symbols in a text editor are normal. Do not edit them.

| Table | What a row represents |
| --- | --- |
| subjects | One subject, with its ID, deadline, difficulty, total and remaining minutes |
| availability | One calendar date and its available study minutes |
| study_sessions | One subject's planned minutes on a date, plus completed minutes |
| planner_state | Whether the plan needs generating after an input change |

An ID identifies a particular subject even when two subjects have the same name.
A session's `subject_id` refers to that ID: this is a foreign key. Deleting a
subject also deletes its sessions, so the database cannot keep orphan sessions.

The initialization functions create missing tables but do not erase existing
subjects. Database files are not committed to Git because they contain personal
data, not source code. Tests use separate temporary databases.

## Follow a button click through the code

When you press Save subject:

1. `templates/dashboard.html` sends a POST request containing form fields.
2. `index.py` checks the form's CSRF token, then parses and validates its values.
3. `database.py` inserts the validated subject using SQL parameters.
4. The transaction commits: SQLite keeps the change on disk.
5. Flask redirects the browser to the dashboard and reads the saved data back.

GET means read a page. POST means submit an action. Redirecting after a successful
POST prevents an ordinary page refresh from submitting that action again.

SQL parameters pass values separately from SQL instructions. A subject name is
treated as data, not executable SQL. Jinja also escapes names when displaying
them, so text entered by a user is not treated as page markup.

## Why progress uses a transaction

Recording completion changes two things together: a session's completed minutes
and its subject's remaining minutes. A transaction makes the operation all or
nothing. If a step fails, rollback cancels the unfinished changes.

`BEGIN IMMEDIATE` obtains SQLite's write reservation before reading the values we
will change. Concurrent completion requests therefore cannot both read an old
remaining value and overwrite one another's updates.

The progress form submits an absolute completed total, not an increment. If a
session already has 30 minutes completed and receives 60, the change is 30.
Receiving 60 again produces a change of zero. This helps make repeated completion
submissions safe.

## What regeneration does

`progress.regenerate_plan` reads subjects and availability, subtracts completed
time from daily capacity, and calls the existing scheduling engine. It replaces
pending sessions, keeping completed portions as history, and saves the new plan.

The scheduler may reduce remaining minutes in its own working copies while
allocating blocks. That must never be confused with reducing the actual remaining
work stored in SQLite. Only recording or undoing progress changes actual work.

Missed sessions are not silently marked complete. On regeneration their remaining
work can be scheduled again, provided there is capacity before the deadline.
Unscheduled-work warnings show workload without a pending session today or later.

## Editing, completion, and safety rules

- Total workload includes already completed work. If 2 hours are complete, you
  cannot edit the total to 1 hour.
- Daily availability includes time already studied. It cannot be reduced below
  recorded completion on that date.
- Future sessions cannot be completed early. Today's and past sessions can have
  actual progress recorded.
- Editing subjects or availability invalidates pending work, so generate again.
- Undo restores workload and invalidates pending work to avoid stale allocations.
- Subject deletion is permanent, including its history; the UI asks for confirmation.
- CSRF tokens help reject actions submitted by another site using your browser.
  They are not a login system. This app remains single-user and local-only.

## A useful reading order

1. `database.py`: connections, subject CRUD (create, read, update, delete), SQL.
2. `tests/test_database.py`: small examples of calling these functions.
3. `progress.py`: transactions, regeneration, completion, dashboard summaries.
4. `tests/test_progress.py`: examples of the important business rules.
5. `index.py`: how browser requests call those Python functions.
6. `templates/dashboard.html`: how forms and Jinja loops display the results.
7. `tests/test_web.py`: how a test client checks the whole request flow.

Before moving on, try explaining aloud why generating a plan must not mark work
complete, why subject IDs matter, and why completing a session changes two tables
in one transaction. These are useful interview discussion points grounded in
code you can actually demonstrate.
