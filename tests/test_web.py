from datetime import date, timedelta

from index import app, format_duration


def valid_form_data(today=None):
    today = today or date.today()
    return {
        "name": ["Math", "Python"],
        "difficulty": ["5", "3"],
        "deadline": [
            (today + timedelta(days=3)).isoformat(),
            (today + timedelta(days=10)).isoformat(),
        ],
        "workload": ["3", "1.5"],
        "availability_date": [
            today.isoformat(),
            (today + timedelta(days=1)).isoformat(),
        ],
        "availability_hours": ["1.5", "2"],
    }


def test_home_page_loads_with_phase_two_fields():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"StudyAI" in response.data
    assert b'name="deadline"' in response.data
    assert b'name="workload"' in response.data
    assert b"+ Add Date" in response.data


def test_valid_form_displays_grouped_study_sessions():
    client = app.test_client()

    response = client.post("/", data=valid_form_data())

    assert response.status_code == 200
    assert b"Your Study Plan" in response.data
    assert b"Math" in response.data
    assert b"1 hr 30 min" in response.data
    assert b"sessions" not in response.data


def test_successful_form_preserves_submitted_values():
    client = app.test_client()

    response = client.post("/", data=valid_form_data())

    assert response.status_code == 200
    assert b'value="Math"' in response.data
    assert b'value="1.5"' in response.data


def test_invalid_form_preserves_values_and_displays_error():
    client = app.test_client()
    today = date.today()
    data = valid_form_data(today)
    data["workload"] = ["", "1.5"]

    response = client.post("/", data=data)

    assert response.status_code == 400
    assert b"Complete all fields for subject 1" in response.data
    assert b'value="Math"' in response.data
    assert b"Traceback" not in response.data


def test_empty_form_displays_a_friendly_error():
    client = app.test_client()
    today = date.today()

    response = client.post(
        "/",
        data={
            "name": "",
            "difficulty": "",
            "deadline": "",
            "workload": "",
            "availability_date": today.isoformat(),
            "availability_hours": "0",
        },
    )

    assert response.status_code == 400
    assert b"Add at least one subject" in response.data


def test_availability_can_extend_beyond_first_seven_days():
    client = app.test_client()
    today = date.today()
    later_date = today + timedelta(days=10)

    response = client.post(
        "/",
        data={
            "name": "Math",
            "difficulty": "5",
            "deadline": later_date.isoformat(),
            "workload": "0.5",
            "availability_date": later_date.isoformat(),
            "availability_hours": "0.5",
        },
    )

    assert response.status_code == 200
    assert later_date.strftime("%A, %d %B %Y").encode() in response.data
    assert b"30 min" in response.data


def test_duration_is_displayed_compactly():
    assert format_duration(0) == "0 min"
    assert format_duration(15) == "15 min"
    assert format_duration(60) == "1 hr"
    assert format_duration(75) == "1 hr 15 min"
    assert format_duration(330) == "5 hr 30 min"


def test_unfinished_work_warning_is_displayed():
    client = app.test_client()
    today = date.today()

    response = client.post(
        "/",
        data={
            "name": "Math",
            "difficulty": "5",
            "deadline": (today + timedelta(days=3)).isoformat(),
            "workload": "5",
            "availability_date": today.isoformat(),
            "availability_hours": "0.5",
        },
    )

    assert response.status_code == 200
    assert b"Unfinished Work" in response.data
    assert b"270 minutes remaining" in response.data
