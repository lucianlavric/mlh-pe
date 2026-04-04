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
