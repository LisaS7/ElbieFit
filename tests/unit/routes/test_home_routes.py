def test_home_contains_title(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to ElbieFit" in response.text


def test_health_returns_status(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_meta_endpoint_returns_basic_info(client):
    response = client.get("/meta")
    body = response.json()

    assert response.status_code == 200
    assert body["app_name"] == "ElbieFit"
    assert isinstance(body["version"], str)
    assert body["version"]
