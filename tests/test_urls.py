import json


def test_list_urls_empty(client):
    response = client.get("/urls")
    assert response.status_code == 200
    assert response.get_json() == []


def test_list_urls_with_data(client, sample_url):
    response = client.get("/urls")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["short_code"] == "abc123"


def test_list_urls_invalid_page(client):
    response = client.get("/urls?page=abc")
    assert response.status_code == 400


def test_get_url_found(client, sample_url):
    response = client.get(f"/urls/{sample_url.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["short_code"] == "abc123"
    assert data["original_url"] == "https://example.com/long-url"


def test_get_url_not_found(client):
    response = client.get("/urls/9999")
    assert response.status_code == 404


def test_get_url_by_code_found(client, sample_url):
    response = client.get("/urls/code/abc123")
    assert response.status_code == 200
    data = response.get_json()
    assert data["original_url"] == "https://example.com/long-url"


def test_get_url_by_code_not_found(client):
    response = client.get("/urls/code/nonexistent")
    assert response.status_code == 404


# --- POST /shorten ---


def test_shorten_url_success(client, sample_user):
    response = client.post(
        "/shorten",
        data=json.dumps({"url": "https://example.com/test", "user_id": sample_user.id}),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["original_url"] == "https://example.com/test"
    assert data["is_active"] is True
    assert len(data["short_code"]) == 6


def test_shorten_url_custom_code(client, sample_user):
    response = client.post(
        "/shorten",
        data=json.dumps({
            "url": "https://example.com/custom",
            "user_id": sample_user.id,
            "short_code": "CUSTOM",
        }),
        content_type="application/json",
    )
    assert response.status_code == 201
    assert response.get_json()["short_code"] == "CUSTOM"


def test_shorten_url_duplicate_code(client, sample_user, sample_url):
    response = client.post(
        "/shorten",
        data=json.dumps({
            "url": "https://example.com/dup",
            "user_id": sample_user.id,
            "short_code": "abc123",
        }),
        content_type="application/json",
    )
    assert response.status_code == 409


def test_shorten_url_missing_url(client, sample_user):
    response = client.post(
        "/shorten",
        data=json.dumps({"user_id": sample_user.id}),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_shorten_url_invalid_url(client, sample_user):
    response = client.post(
        "/shorten",
        data=json.dumps({"url": "not-a-url", "user_id": sample_user.id}),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_shorten_url_missing_user_id(client):
    response = client.post(
        "/shorten",
        data=json.dumps({"url": "https://example.com/test"}),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_shorten_url_invalid_user_id(client):
    response = client.post(
        "/shorten",
        data=json.dumps({"url": "https://example.com/test", "user_id": 9999}),
        content_type="application/json",
    )
    assert response.status_code == 404


def test_shorten_url_no_json_body(client):
    response = client.post("/shorten", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_shorten_creates_event(client, sample_user):
    from app.models.event import Event

    response = client.post(
        "/shorten",
        data=json.dumps({"url": "https://example.com/event-test", "user_id": sample_user.id}),
        content_type="application/json",
    )
    assert response.status_code == 201
    events = list(Event.select().where(Event.event_type == "created"))
    assert len(events) >= 1


# --- GET /<short_code> redirect ---


def test_redirect_success(client, sample_url):
    response = client.get(f"/{sample_url.short_code}")
    assert response.status_code == 302
    assert response.headers["Location"] == "https://example.com/long-url"


def test_redirect_logs_event(client, sample_url):
    """The Unseen Observer: every redirect must be recorded."""
    from app.models.event import Event

    client.get(f"/{sample_url.short_code}")
    events = list(Event.select().where(Event.event_type == "redirect"))
    assert len(events) == 1
    assert events[0].url.id == sample_url.id


def test_redirect_not_found(client):
    response = client.get("/XXXXXX")
    assert response.status_code == 404


def test_redirect_inactive_url(client, sample_user):
    """The Slumbering Guide: inactive URLs must not redirect."""
    from app.models.url import Url

    url = Url.create(
        user=sample_user,
        short_code="DEAD01",
        original_url="https://example.com/dead",
        title="Inactive",
        is_active=False,
        created_at="2025-01-01 00:00:00",
        updated_at="2025-01-01 00:00:00",
    )
    response = client.get(f"/{url.short_code}")
    assert response.status_code == 410


def test_redirect_inactive_no_event(client, sample_user):
    """The Slumbering Guide: inactive URLs must leave no footprint."""
    from app.models.event import Event
    from app.models.url import Url

    url = Url.create(
        user=sample_user,
        short_code="DEAD02",
        original_url="https://example.com/dead2",
        title="Inactive",
        is_active=False,
        created_at="2025-01-01 00:00:00",
        updated_at="2025-01-01 00:00:00",
    )
    client.get(f"/{url.short_code}")
    events = list(Event.select().where(Event.event_type == "redirect"))
    assert len(events) == 0


# --- PUT /urls/<id> ---


def test_update_url_title(client, sample_url):
    response = client.put(
        f"/urls/{sample_url.id}",
        data=json.dumps({"title": "New Title"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.get_json()["title"] == "New Title"


def test_update_url_original(client, sample_url):
    response = client.put(
        f"/urls/{sample_url.id}",
        data=json.dumps({"url": "https://new-example.com/updated"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.get_json()["original_url"] == "https://new-example.com/updated"


def test_update_url_deactivate(client, sample_url):
    response = client.put(
        f"/urls/{sample_url.id}",
        data=json.dumps({"is_active": False}),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.get_json()["is_active"] is False


def test_update_url_invalid_url(client, sample_url):
    response = client.put(
        f"/urls/{sample_url.id}",
        data=json.dumps({"url": "bad"}),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_update_url_invalid_is_active(client, sample_url):
    response = client.put(
        f"/urls/{sample_url.id}",
        data=json.dumps({"is_active": "yes"}),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_update_url_not_found(client):
    response = client.put(
        "/urls/9999",
        data=json.dumps({"title": "X"}),
        content_type="application/json",
    )
    assert response.status_code == 404


def test_update_url_no_body(client, sample_url):
    response = client.put(f"/urls/{sample_url.id}", data="bad", content_type="text/plain")
    assert response.status_code == 400


def test_update_url_empty_fields(client, sample_url):
    response = client.put(
        f"/urls/{sample_url.id}",
        data=json.dumps({"foo": "bar"}),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_update_creates_event(client, sample_url):
    from app.models.event import Event

    client.put(
        f"/urls/{sample_url.id}",
        data=json.dumps({"title": "Updated"}),
        content_type="application/json",
    )
    events = list(Event.select().where(Event.event_type == "updated"))
    assert len(events) >= 1


# --- DELETE /urls/<id> ---


def test_delete_url(client, sample_url):
    response = client.delete(f"/urls/{sample_url.id}")
    assert response.status_code == 200
    # Verify it's deactivated
    from app.models.url import Url

    url = Url.get_by_id(sample_url.id)
    assert url.is_active is False


def test_delete_url_not_found(client):
    response = client.delete("/urls/9999")
    assert response.status_code == 404


def test_delete_creates_event(client, sample_url):
    from app.models.event import Event

    client.delete(f"/urls/{sample_url.id}")
    events = list(Event.select().where(Event.event_type == "deleted"))
    assert len(events) >= 1
