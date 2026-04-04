def test_list_events_empty(client):
    response = client.get("/events")
    assert response.status_code == 200
    assert response.get_json() == []


def test_list_events_with_data(client, sample_event):
    response = client.get("/events")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["event_type"] == "created"


def test_list_events_invalid_page(client):
    response = client.get("/events?page=abc")
    assert response.status_code == 400


def test_get_event_found(client, sample_event):
    response = client.get(f"/events/{sample_event.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["event_type"] == "created"


def test_get_event_not_found(client):
    response = client.get("/events/9999")
    assert response.status_code == 404
