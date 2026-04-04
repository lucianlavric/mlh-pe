from playhouse.shortcuts import model_to_dict

from app.models.event import Event
from app.models.url import Url
from app.models.user import User


def test_create_user(client):
    user = User.create(
        username="modeltest",
        email="model@test.com",
        created_at="2025-06-01 00:00:00",
    )
    assert user.id is not None
    assert user.username == "modeltest"
    assert user.email == "model@test.com"


def test_create_url(client, sample_user):
    url = Url.create(
        user=sample_user,
        short_code="xyz789",
        original_url="https://example.com",
        title="Model Test",
        is_active=True,
        created_at="2025-06-01 00:00:00",
        updated_at="2025-06-01 00:00:00",
    )
    assert url.id is not None
    assert url.short_code == "xyz789"
    assert url.user.id == sample_user.id


def test_create_event(client, sample_url, sample_user):
    event = Event.create(
        url=sample_url,
        user=sample_user,
        event_type="created",
        timestamp="2025-06-01 00:00:00",
        details="{}",
    )
    assert event.id is not None
    assert event.event_type == "created"


def test_user_to_dict(client, sample_user):
    d = model_to_dict(sample_user)
    assert d["username"] == "testuser"
    assert d["email"] == "test@example.com"
    assert "id" in d


def test_url_to_dict(client, sample_url):
    d = model_to_dict(sample_url)
    assert d["short_code"] == "abc123"
    assert d["original_url"] == "https://example.com/long-url"
    assert d["user"]["username"] == "testuser"


def test_event_to_dict(client, sample_event):
    d = model_to_dict(sample_event)
    assert d["event_type"] == "created"
    assert d["url"]["short_code"] == "abc123"
    assert d["user"]["username"] == "testuser"
