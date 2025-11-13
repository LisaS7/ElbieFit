from fastapi import HTTPException

from app.main import app


# Dummy routes
@app.get("/raise-401")
def raise_401():
    raise HTTPException(status_code=401, detail="Nope")


@app.get("/raise-418")
def raise_418():
    raise HTTPException(status_code=418, detail="I am a teapot")


@app.get("/raise-exception")
def raise_exception():
    raise ValueError("Kaboom")


def test_401_redirects_to_login(client):
    response = client.get("/raise-401", follow_redirects=False)
    assert response.status_code == 307 or response.status_code == 302
    assert response.headers["location"] == "/auth/login"


def test_http_exception_renders_error_template(client):
    response = client.get("/raise-418")
    assert response.status_code == 418
    assert "I am a teapot" in response.text


def test_unhandled_exception_renders_gremlins(client):
    response = client.get("/raise-exception")
    assert response.status_code == 500
    assert "Gremlins." in response.text
