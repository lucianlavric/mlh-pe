def test_list_users_empty(client):
    response = client.get("/users")
    assert response.status_code == 200
    assert response.get_json() == []


def test_list_users_with_data(client, sample_user):
    response = client.get("/users")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["username"] == "testuser"


def test_list_users_pagination(client):
    from app.models.user import User

    for i in range(5):
        User.create(
            username=f"user{i}",
            email=f"user{i}@test.com",
            created_at="2025-01-01 00:00:00",
        )
    response = client.get("/users?page=1&per_page=2")
    assert response.status_code == 200
    assert len(response.get_json()) == 2

    response = client.get("/users?page=3&per_page=2")
    assert response.status_code == 200
    assert len(response.get_json()) == 1


def test_list_users_invalid_page(client):
    response = client.get("/users?page=abc")
    assert response.status_code == 400
    assert "Invalid" in response.get_json()["error"]


def test_list_users_negative_page(client):
    response = client.get("/users?page=-1")
    assert response.status_code == 400


def test_get_user_found(client, sample_user):
    response = client.get(f"/users/{sample_user.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["username"] == "testuser"


def test_get_user_not_found(client):
    response = client.get("/users/9999")
    assert response.status_code == 404
    assert "not found" in response.get_json()["error"].lower()
