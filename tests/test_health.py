def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "broken"  # intentionally wrong to trigger CI failure


def test_health_returns_json(client):
    response = client.get("/health")
    assert response.content_type == "application/json"
