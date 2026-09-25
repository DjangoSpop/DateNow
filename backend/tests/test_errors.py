import pytest
from fastapi.testclient import TestClient

from app.errors import AppError
from app.main import app
from helpers import API, assert_error

BOOM_PATH = "/__test__/boom"
APP_ERROR_PATH = "/__test__/app-error"


@pytest.fixture(scope="module", autouse=True)
def test_routes():
    async def boom():
        raise RuntimeError("secret internal detail: password=hunter2")

    async def app_error():
        raise AppError(418, "TEAPOT", "I'm a teapot", fields={"x": "y"})

    app.add_api_route(BOOM_PATH, boom, methods=["GET"])
    app.add_api_route(APP_ERROR_PATH, app_error, methods=["GET"])
    yield
    app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", None) not in (BOOM_PATH, APP_ERROR_PATH)]


def test_404_envelope(client):
    err = assert_error(client.get(f"{API}/does-not-exist"), 404, "NOT_FOUND")
    assert "fields" not in err


def test_405_envelope(client):
    assert_error(client.delete("/health"), 405, "METHOD_NOT_ALLOWED")


def test_422_envelope(client):
    resp = client.post(f"{API}/auth/login", json={"email": "bad"})
    err = assert_error(resp, 422, "VALIDATION_ERROR")
    assert set(err["fields"]) == {"email", "password"}
    assert all(isinstance(v, str) for v in err["fields"].values())


def test_422_non_json_body(client):
    resp = client.post(f"{API}/auth/login", content=b"not json", headers={"Content-Type": "application/json"})
    assert_error(resp, 422, "VALIDATION_ERROR")


def test_app_error_envelope(client):
    resp = client.get(APP_ERROR_PATH)
    assert resp.status_code == 418
    assert resp.json() == {"error": {"code": "TEAPOT", "message": "I'm a teapot", "fields": {"x": "y"}}}


def test_500_envelope_hides_internals():
    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get(BOOM_PATH)
    assert resp.status_code == 500
    assert resp.json() == {"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}
    assert "hunter2" not in resp.text and "RuntimeError" not in resp.text


def test_401_has_www_authenticate(client):
    resp = client.get(f"{API}/users/me")
    assert resp.headers.get("www-authenticate") == "Bearer"
