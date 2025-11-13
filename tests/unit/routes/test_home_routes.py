def test_home_contains_title(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to ElbieFit" in response.text


def test_health_returns_status(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
