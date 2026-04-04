def test_404_unknown_route(client):
    response = client.get("/nonexistent-route")
    assert response.status_code == 404
    data = response.get_json()
    assert "not found" in data["error"].lower()


def test_404_response_is_json(client):
    response = client.get("/does-not-exist")
    assert response.content_type == "application/json"
    assert response.status_code == 404


def test_405_wrong_method(client):
    response = client.post("/health")
    assert response.status_code == 405
    data = response.get_json()
    assert data["error"] == "Method not allowed"


def test_bad_pagination_page_string(client):
    response = client.get("/users?page=notanumber")
    assert response.status_code == 400


def test_bad_pagination_per_page_zero(client):
    response = client.get("/urls?per_page=0")
    assert response.status_code == 400


def test_bad_pagination_negative(client):
    response = client.get("/events?page=-5&per_page=-1")
    assert response.status_code == 400
