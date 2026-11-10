import os

from backend.config.settings import settings


def test_upload_rejects_python_and_traversal(client):
    r = client.post("/api/ocr/upload-and-parse",
                    files={"file": ("../../plugins/evil_plugin.py", b"print('x')")}, data={"doc_type": "auto"})
    assert r.status_code == 400
    assert not (settings.plugins_dir / "evil_plugin.py").exists()


def test_upload_stays_in_uploads_dir(client):
    client.post("/api/ocr/upload-and-parse",
                files={"file": ("..\\..\\x.pdf", b"%PDF-1.4")}, data={"doc_type": "auto"})
    names = os.listdir(settings.uploads_dir)
    assert any(n.startswith("x_") and n.endswith(".pdf") for n in names)
    assert not (settings.data_dir.parent / "x.pdf").exists()


def test_cross_site_requests_are_refused(client):
    assert client.post("/api/plugins/reload", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.delete("/api/finance/transactions/1", headers={"Origin": "https://evil.example"}).status_code == 403


def test_foreign_host_is_refused(app):
    from starlette.testclient import TestClient
    with TestClient(app, base_url="http://evil.example") as c:
        assert c.get("/api/agents").status_code == 403


def test_local_origin_is_allowed(client):
    r = client.get("/api/agents", headers={"Origin": "http://127.0.0.1:5173"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_external_data_dir_is_seeded():
    assert settings.data_dir == settings.uploads_dir.parent
    assert settings.ngo_profile_path.exists()
    assert settings.ngo_profile_path.parent == settings.data_dir / "config"
