import pytest

from backend.config.settings import settings


@pytest.fixture()
def token(monkeypatch):
    monkeypatch.setattr(settings, "api_token", "jeton-de-test-123")
    return "jeton-de-test-123"


def test_requests_without_token_are_refused(client, token):
    assert client.get("/api/agents").status_code == 401
    assert client.get("/api/agents", headers={"X-AFMI-Token": "mauvais"}).status_code == 401


def test_header_token_is_accepted(client, token):
    assert client.get("/api/agents", headers={"X-AFMI-Token": token}).status_code == 200


def test_page_opened_with_token_gets_a_session_cookie(client, token):
    r = client.get(f"/api/agents?afmi_token={token}")
    assert r.status_code == 200
    cookie = r.headers["set-cookie"]
    assert "afmi_session=" in cookie and "HttpOnly" in cookie and "samesite=strict" in cookie.lower()
    # Les requêtes suivantes de la page passent grâce au cookie
    assert client.get("/api/agents").status_code == 200


def test_no_token_configured_keeps_local_dev_mode(client, monkeypatch):
    monkeypatch.setattr(settings, "api_token", "")
    client.cookies.clear()
    assert client.get("/api/agents").status_code == 200
