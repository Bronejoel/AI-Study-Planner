"""Flask routes: validate requests, call persistence functions, render templates."""
import os
import secrets
import sqlite3
from datetime import date, timedelta

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

import database
import progress
from planner import hours_to_minutes
from validation import parse_daily_availability


def format_duration(total_minutes):
    hours, minutes = divmod(total_minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hr")
    if minutes or not parts:
        parts.append(f"{minutes} min")
    return " ".join(parts)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=str(database.DATABASE_PATH),
        SECRET_KEY=os.environ.get("STUDYAI_SECRET_KEY") or secrets.token_hex(32),
        MAX_CONTENT_LENGTH=128 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        CSRF_ENABLED=True,
    )
    if test_config:
        app.config.update(test_config)
    app.jinja_env.filters["duration"] = format_duration

    @app.before_request
    def prepare_request():
        # Lazy initialization keeps imports/tests away from the real database.
        if not app.config.get("_DB_READY"):
            progress.initialize_progress(app.config["DATABASE"])
            app.config["_DB_READY"] = True
        session.setdefault("csrf_token", secrets.token_hex(32))
        session.setdefault("create_token", secrets.token_hex(32))
        if request.method == "POST" and app.config["CSRF_ENABLED"]:
            token = request.form.get("csrf_token", "")
            if not secrets.compare_digest(token, session["csrf_token"]):
                abort(400, description="This form expired. Refresh the page and try again.")

    def dashboard(error=None, form=None, edit_id=None, availability_rows=None, status=200):
        data = progress.dashboard_data(app.config["DATABASE"])
        if availability_rows is not None:
            data["availability_rows"] = availability_rows
        elif not data["availability_rows"]:
            data["availability_rows"] = [
                {"date": (data["today"] + timedelta(days=i)).isoformat(), "hours": 0}
                for i in range(7)
            ]
        return render_template("dashboard.html", **data, error=error,
                               form=form or {}, edit_id=edit_id), status

    def parse_subject_form():
        try:
            difficulty = int(request.form.get("difficulty", ""))
            deadline = date.fromisoformat(request.form.get("deadline", ""))
            hours = float(request.form.get("workload", ""))
        except ValueError:
            raise ValueError("Enter a whole-number difficulty, a valid deadline and numeric workload.")
        total_minutes = hours_to_minutes(hours)
        name = database._validate_subject_details(
            request.form.get("name", ""), difficulty, deadline,
            total_minutes,
        )
        return dict(name=name, difficulty=difficulty, deadline=deadline,
                    total_minutes=total_minutes)

    @app.get("/")
    def home():
        return dashboard()

    @app.post("/subjects")
    def add_subject():
        if request.form.get("create_token") != session["create_token"]:
            return dashboard(error="This subject form was already submitted. Refresh before adding another.", status=409)
        try:
            values = parse_subject_form()
            if values["deadline"] < date.today():
                raise ValueError("A new subject's deadline must be today or later.")
            database.create_subject(**values, database_path=app.config["DATABASE"])
        except ValueError as error:
            return dashboard(error=str(error), form=request.form, status=400)
        session["create_token"] = secrets.token_hex(32)
        flash("Subject saved. Generate a plan when your availability is ready.")
        return redirect(url_for("home", _anchor="subjects"), code=303)

    @app.post("/subjects/<int:subject_id>/edit")
    def edit_subject(subject_id):
        try:
            found = database.update_subject(subject_id, **parse_subject_form(), database_path=app.config["DATABASE"])
        except ValueError as error:
            return dashboard(error=str(error), form=request.form, edit_id=subject_id, status=400)
        if not found:
            abort(404)
        flash("Subject updated. Completed progress is preserved; regenerate the pending plan.")
        return redirect(url_for("home", _anchor="subjects"), code=303)

    @app.post("/subjects/<int:subject_id>/delete")
    def remove_subject(subject_id):
        if not database.delete_subject(subject_id, app.config["DATABASE"]):
            abort(404)
        flash("Subject and its sessions deleted. Regenerate the remaining plan.")
        return redirect(url_for("home", _anchor="subjects"), code=303)

    @app.post("/availability")
    def availability():
        try:
            values = parse_daily_availability(
                request.form.getlist("availability_date"),
                request.form.getlist("availability_hours"),
                today=date.today(),
            )
            progress.save_availability(values, app.config["DATABASE"])
        except ValueError as error:
            dates = request.form.getlist("availability_date")
            hours = request.form.getlist("availability_hours")
            rows = [{"date": dates[i] if i < len(dates) else "",
                     "hours": hours[i] if i < len(hours) else ""}
                    for i in range(max(len(dates), len(hours), 1))]
            return dashboard(error=str(error), availability_rows=rows, status=400)
        flash("Availability saved. Generate a plan to use these hours.")
        return redirect(url_for("home", _anchor="availability-section"), code=303)

    @app.post("/plan")
    def generate():
        try:
            progress.regenerate_plan(app.config["DATABASE"])
        except ValueError as error:
            return dashboard(error=str(error), status=400)
        flash("Plan saved. Only completed study reduces your remaining workload.")
        return redirect(url_for("home", _anchor="study-plan"), code=303)

    @app.post("/sessions/<int:session_id>/progress")
    def complete(session_id):
        try:
            try:
                target = int(request.form.get("completed_minutes", ""))
            except ValueError:
                raise ValueError("Enter completed time as a whole number of minutes.")
            found = progress.record_completion(session_id, target, app.config["DATABASE"])
        except ValueError as error:
            return dashboard(error=str(error), status=400)
        if not found:
            abort(404, description="This session was replaced or removed. Refresh your plan.")
        flash("Progress saved." if target else "Completion undone. Generate a fresh plan.")
        return redirect(url_for("home", _anchor="study-plan"), code=303)

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def request_error(error):
        return render_template("request_error.html", message=error.description), error.code

    @app.errorhandler(sqlite3.OperationalError)
    def database_error(error):
        app.logger.exception("Database operation failed")
        return render_template("request_error.html",
                               message="The database is unavailable or busy. Please try again."), 503

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=5001)
