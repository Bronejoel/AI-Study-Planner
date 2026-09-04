from index import app


def test_home_page_loads():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"StudyAI" in response.data


def test_valid_form_displays_a_weekly_plan():
    client = app.test_client()

    response = client.post(
        "/",
        data={
            "name": ["Math", "Python"],
            "difficulty": ["5", "3"],
            "days": ["2", "7"],
            "hours": "1.5",
        },
    )

    assert response.status_code == 200
    assert b"Weekly Study Plan" in response.data
    assert b"Math" in response.data
    assert b"Python" in response.data


def test_invalid_number_displays_a_friendly_error():
    client = app.test_client()

    response = client.post(
        "/",
        data={
            "name": "Math",
            "difficulty": "difficult",
            "days": "2",
            "hours": "1",
        },
    )

    assert response.status_code == 400
    assert b"must be whole numbers" in response.data
    assert b"Traceback" not in response.data


def test_empty_form_displays_a_friendly_error():
    client = app.test_client()

    response = client.post(
        "/",
        data={"name": "", "difficulty": "", "days": "", "hours": "2"},
    )

    assert response.status_code == 400
    assert b"Add at least one subject" in response.data
