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


def test_create_event(client, sample_url, sample_user):
    import json
    response = client.post(
        "/events",
        data=json.dumps({
            "url_id": sample_url.id,
            "user_id": sample_user.id,
            "event_type": "click",
            "details": {"referrer": "https://google.com"},
        }),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["event_type"] == "click"
    assert data["url_id"] == sample_url.id


def test_create_event_missing_fields(client):
    import json
    response = client.post(
        "/events",
        data=json.dumps({"url_id": 1}),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_filter_events_by_url_id(client, sample_event):
    response = client.get(f"/events?url_id={sample_event.url_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert all(e["url_id"] == sample_event.url_id for e in data)


def test_filter_events_by_event_type(client, sample_event):
    response = client.get("/events?event_type=created")
    assert response.status_code == 200
    data = response.get_json()
    assert all(e["event_type"] == "created" for e in data)


def test_event_details_is_json_object(client, sample_event):
    response = client.get(f"/events/{sample_event.id}")
    data = response.get_json()
    assert isinstance(data["details"], dict)


def test_delete_event(client, sample_event):
    response = client.delete(f"/events/{sample_event.id}")
    assert response.status_code == 204
