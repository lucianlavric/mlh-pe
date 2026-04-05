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


# --- POST /users ---


def test_create_user(client):
    import json
    response = client.post(
        "/users",
        data=json.dumps({"username": "newuser", "email": "new@test.com"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@test.com"
    assert "id" in data


def test_create_user_missing_username(client):
    import json
    response = client.post(
        "/users",
        data=json.dumps({"email": "no@user.com"}),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_create_user_invalid_username(client):
    import json
    response = client.post(
        "/users",
        data=json.dumps({"username": 123, "email": "bad@test.com"}),
        content_type="application/json",
    )
    assert response.status_code == 400


# --- PUT /users/<id> ---


def test_update_user(client, sample_user):
    import json
    response = client.put(
        f"/users/{sample_user.id}",
        data=json.dumps({"username": "updated_name"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.get_json()["username"] == "updated_name"


def test_update_user_not_found(client):
    import json
    response = client.put(
        "/users/9999",
        data=json.dumps({"username": "x"}),
        content_type="application/json",
    )
    assert response.status_code == 404


def test_update_user_invalid_type(client, sample_user):
    import json
    response = client.put(
        f"/users/{sample_user.id}",
        data=json.dumps({"username": 999}),
        content_type="application/json",
    )
    assert response.status_code == 400


# --- POST /users/bulk ---


def test_bulk_upload_users(client):
    import io
    csv_data = "username,email,created_at\nbulk1,bulk1@test.com,2025-01-01 00:00:00\nbulk2,bulk2@test.com,2025-01-01 00:00:00"
    data = {"file": (io.BytesIO(csv_data.encode()), "users.csv")}
    response = client.post("/users/bulk", data=data, content_type="multipart/form-data")
    assert response.status_code == 201
    assert response.get_json()["count"] == 2
