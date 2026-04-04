import pytest
from peewee import SqliteDatabase

from app.database import db
from app.models.event import Event
from app.models.url import Url
from app.models.user import User

MODELS = [User, Url, Event]


@pytest.fixture()
def app():
    test_db = SqliteDatabase(":memory:")
    db.initialize(test_db)
    db.connect()
    db.create_tables(MODELS)

    from app import create_app

    application = create_app(config={"TESTING": True})
    application.config["TESTING"] = True

    yield application

    db.drop_tables(MODELS)
    db.close()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def sample_user():
    return User.create(
        username="testuser",
        email="test@example.com",
        created_at="2025-01-01 00:00:00",
    )


@pytest.fixture()
def sample_url(sample_user):
    return Url.create(
        user=sample_user,
        short_code="abc123",
        original_url="https://example.com/long-url",
        title="Test URL",
        is_active=True,
        created_at="2025-01-01 00:00:00",
        updated_at="2025-01-02 00:00:00",
    )


@pytest.fixture()
def sample_event(sample_url, sample_user):
    return Event.create(
        url=sample_url,
        user=sample_user,
        event_type="created",
        timestamp="2025-01-01 00:00:00",
        details='{"short_code":"abc123"}',
    )
