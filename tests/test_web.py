"""Integration tests use a separate database and real CSRF-protected forms."""
from datetime import date, timedelta

import pytest

import database
import progress
from index import create_app, format_duration


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "web.db"), "SECRET_KEY": "test-secret"})


@pytest.fixture
def client(app):
    client = app.test_client()
    client.get("/")
    return client


def post(client, path, data=None, follow_redirects=False):
    with client.session_transaction() as session:
        tokens = {"csrf_token": session["csrf_token"], "create_token": session["create_token"]}
    return client.post(path, data={**tokens, **(data or {})}, follow_redirects=follow_redirects)


def add(client, **overrides):
    data = dict(name="Python", difficulty="4", deadline=(date.today() + timedelta(days=4)).isoformat(), workload="3")
    data.update(overrides)
    return post(client, "/subjects", data)


def make_plan(client):
    add(client)
    post(client, "/availability", dict(availability_date=date.today().isoformat(), availability_hours="2"))
    return post(client, "/plan")


def test_home_page_loads_with_saved_workflow(client):
    page = client.get("/")
    assert page.status_code == 200
    for label in (b"StudyAI", b'name="deadline"', b'name="workload"', b"+ Add Date", b"No saved subjects"):
        assert label in page.data


def test_subject_survives_redirect_and_app_restart(client, app):
    assert add(client).status_code == 303
    second = create_app({"TESTING": True, "DATABASE": app.config["DATABASE"]}).test_client()
    assert b"Python" in second.get("/").data


def test_invalid_create_preserves_values_without_writing(client, app):
    response = add(client, name="Keep this name", workload="")
    assert response.status_code == 400
    assert b'value="Keep this name"' in response.data
    assert database.get_subjects(app.config["DATABASE"]) == []


def test_create_duplicate_submission_is_not_inserted(client, app):
    with client.session_transaction() as session:
        data = dict(csrf_token=session["csrf_token"], create_token=session["create_token"],
                    name="Python", difficulty=4, deadline=date.today().isoformat(), workload=1)
    assert client.post("/subjects", data=data).status_code == 303
    assert client.post("/subjects", data=data).status_code == 409
    assert len(database.get_subjects(app.config["DATABASE"])) == 1


def test_csrf_is_required(client, app):
    assert client.post("/subjects", data={"name": "Bad"}).status_code == 400
    assert database.get_subjects(app.config["DATABASE"]) == []


def test_valid_form_displays_compact_saved_plan(client, app):
    assert make_plan(client).status_code == 303
    response = client.get("/")
    assert b"2 hr" in response.data
    assert b"Mark as completed" in response.data
    assert b"Unscheduled work" in response.data
    assert database.get_subjects(app.config["DATABASE"])[0]["remaining_minutes"] == 180


def test_complete_undo_and_regenerate(client, app):
    make_plan(client)
    path = app.config["DATABASE"]
    entry = next(iter(progress.dashboard_data(path)["days"].values()))[0]
    endpoint = f"/sessions/{entry['id']}/progress"
    assert post(client, endpoint, {"completed_minutes": "30"}).status_code == 303
    assert post(client, endpoint, {"completed_minutes": "30"}).status_code == 303
    assert database.get_subjects(path)[0]["remaining_minutes"] == 150
    assert post(client, "/plan").status_code == 303
    assert post(client, endpoint, {"completed_minutes": "0"}).status_code == 303
    assert database.get_subjects(path)[0]["remaining_minutes"] == 180
    assert post(client, "/plan").status_code == 303


def test_edit_delete_and_missing_subject(client, app):
    add(client)
    sid = database.get_subjects(app.config["DATABASE"])[0]["id"]
    assert post(client, f"/subjects/{sid}/edit", dict(name="Advanced Python", difficulty="5",
               deadline=date.today().isoformat(), workload="4")).status_code == 303
    assert b"Advanced Python" in client.get("/").data
    assert post(client, f"/subjects/{sid}/delete").status_code == 303
    assert database.get_subjects(app.config["DATABASE"]) == []
    assert post(client, f"/subjects/{sid}/delete").status_code == 404


def test_invalid_edit_preserves_submitted_values(client):
    add(client)
    response = post(client, "/subjects/1/edit", dict(name="My edit", difficulty="9",
                    deadline=date.today().isoformat(), workload="1"))
    assert response.status_code == 400
    assert b'value="My edit"' in response.data


def test_availability_beyond_seven_days_and_blank_rows(client):
    later = (date.today() + timedelta(days=10)).isoformat()
    add(client, deadline=later, workload="0.5")
    response = post(client, "/availability", dict(availability_date=[later, ""], availability_hours=["0.5", ""]))
    assert response.status_code == 303
    assert post(client, "/plan").status_code == 303
    assert b"30 min" in client.get("/").data


def test_invalid_availability_preserves_values(client):
    response = post(client, "/availability", dict(availability_date=[date.today().isoformat(), ""],
                    availability_hours=["2", "1"]))
    assert response.status_code == 400
    assert b'value="2"' in response.data
    assert b"Choose a study date" in response.data


def test_generate_requires_subjects_and_availability(client):
    assert post(client, "/plan").status_code == 400
    add(client)
    assert post(client, "/plan").status_code == 400


def test_invalid_completion_and_unknown_session(client):
    make_plan(client)
    assert post(client, "/sessions/1/progress", {"completed_minutes": "many"}).status_code == 400
    assert post(client, "/sessions/1/progress", {"completed_minutes": "999"}).status_code == 400
    assert post(client, "/sessions/999/progress", {"completed_minutes": "0"}).status_code == 404


def test_html_names_are_escaped(client):
    add(client, name="<script>alert(1)</script>")
    page = client.get("/").data
    assert b"<script>alert(1)</script>" not in page
    assert b"&lt;script&gt;" in page


def test_state_changes_require_post(client):
    assert client.get("/subjects/1/delete").status_code == 405
    assert client.get("/plan").status_code == 405


@pytest.mark.parametrize("minutes, expected", [(0, "0 min"), (15, "15 min"), (60, "1 hr"),
                                           (75, "1 hr 15 min"), (330, "5 hr 30 min")])
def test_duration_is_displayed_compactly(minutes, expected):
    assert format_duration(minutes) == expected
